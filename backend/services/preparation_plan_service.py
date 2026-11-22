import asyncio
from datetime import date, datetime, timedelta, timezone

from bson import ObjectId

from repositories.analysis_repository import AnalysisRepository
from repositories.interview_repository import InterviewRepository
from repositories.job_match_repository import JobMatchRepository
from repositories.preparation_plan_repository import (
    PreparationPlanRepository,
    PreparationPlanRepositoryError,
)
from repositories.resume_repository import ResumeRepository
from schemas.preparation_plan_schema import (
    DAY_THEMES,
    GeminiPlanDayPayload,
    GeneratePreparationPlanRequest,
    PreparationPlanDay,
    PreparationPlanListItem,
    PreparationPlanListResponse,
    PreparationPlanResponse,
    PreparationPlanTask,
    UpdatePlanTaskCompletionRequest,
)
from services.gemini_config import get_gemini_model
from services.preparation_plan_evidence_service import build_preparation_plan_evidence
from workflows.preparation_plan_graph import run_preparation_plan_workflow


class PreparationPlanServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _build_tasks(day: GeminiPlanDayPayload) -> list[PreparationPlanTask]:
    tasks: list[PreparationPlanTask] = []
    per_activity = max(10, day.estimated_duration_minutes // max(len(day.learning_activities), 1))

    for index, activity in enumerate(day.learning_activities, start=1):
        tasks.append(
            PreparationPlanTask(
                task_id=f"d{day.day_number}-learn-{index}",
                title=f"Learning activity {index}",
                description=activity,
                task_type="learning",
                estimated_minutes=min(per_activity, 90),
            )
        )

    question_minutes = max(15, day.estimated_duration_minutes // max(len(day.interview_questions), 1))
    for index, question in enumerate(day.interview_questions, start=1):
        tasks.append(
            PreparationPlanTask(
                task_id=f"d{day.day_number}-q-{index}",
                title=f"Practice question {index}",
                description=question,
                task_type="practice_question",
                estimated_minutes=min(question_minutes, 60),
            )
        )

    if day.practical_exercise and day.practical_exercise.strip():
        tasks.append(
            PreparationPlanTask(
                task_id=f"d{day.day_number}-exercise",
                title="Practical exercise",
                description=day.practical_exercise.strip(),
                task_type="exercise",
                estimated_minutes=min(45, day.estimated_duration_minutes),
            )
        )

    tasks.append(
        PreparationPlanTask(
            task_id=f"d{day.day_number}-review",
            title="Day review",
            description=day.completion_criteria,
            task_type="review",
            estimated_minutes=10,
        )
    )
    return tasks


def _progress(days: list[dict]) -> tuple[float, int, int]:
    total = 0
    completed = 0
    for day in days:
        for task in day.get("tasks") or []:
            total += 1
            if task.get("completed"):
                completed += 1
    percent = round((completed / total) * 100.0, 1) if total else 0.0
    return percent, completed, total


def _today_day_number(plan_start: date) -> int | None:
    today = datetime.now(timezone.utc).date()
    delta = (today - plan_start).days + 1
    if 1 <= delta <= 7:
        return delta
    return None


def _document_to_response(document: dict) -> PreparationPlanResponse:
    plan_id = document["_id"]
    if isinstance(plan_id, ObjectId):
        plan_id = str(plan_id)

    days_raw = document.get("days") or []
    days = [PreparationPlanDay.model_validate(d) for d in days_raw]
    progress_percent, tasks_completed, tasks_total = _progress(days_raw)
    plan_start = document.get("plan_start_date")
    if isinstance(plan_start, datetime):
        plan_start = plan_start.date()
    elif isinstance(plan_start, str):
        plan_start = date.fromisoformat(plan_start)

    return PreparationPlanResponse(
        id=str(plan_id),
        user_id=document["user_id"],
        resume_id=document["resume_id"],
        job_match_id=document.get("job_match_id"),
        status=document["status"],
        daily_study_minutes=document["daily_study_minutes"],
        model=document.get("model", ""),
        plan_start_date=plan_start,
        created_at=document["created_at"],
        updated_at=document["updated_at"],
        plan_summary=document.get("plan_summary", ""),
        priority_gaps=document.get("priority_gaps", []),
        days=days,
        progress_percent=progress_percent,
        tasks_completed=tasks_completed,
        tasks_total=tasks_total,
        today_day_number=_today_day_number(plan_start),
    )


def _document_to_list_item(document: dict) -> PreparationPlanListItem:
    plan_id = document["_id"]
    if isinstance(plan_id, ObjectId):
        plan_id = str(plan_id)
    days = document.get("days") or []
    progress, _, _ = _progress(days)
    plan_start = document.get("plan_start_date")
    if isinstance(plan_start, datetime):
        plan_start = plan_start.date()
    elif isinstance(plan_start, str):
        plan_start = date.fromisoformat(plan_start)
    return PreparationPlanListItem(
        id=str(plan_id),
        resume_id=document["resume_id"],
        job_match_id=document.get("job_match_id"),
        status=document["status"],
        daily_study_minutes=document["daily_study_minutes"],
        progress_percent=progress,
        created_at=document["created_at"],
        plan_start_date=plan_start,
    )


def _gemini_days_to_stored(
    gemini_days: list[GeminiPlanDayPayload],
    plan_start: date,
) -> list[dict]:
    stored: list[dict] = []
    for day in sorted(gemini_days, key=lambda item: item.day_number):
        scheduled = plan_start + timedelta(days=day.day_number - 1)
        tasks = _build_tasks(day)
        record = PreparationPlanDay(
            day_number=day.day_number,
            relative_label=f"Day {day.day_number}",
            scheduled_date=scheduled,
            theme=DAY_THEMES[day.day_number],
            learning_objective=day.learning_objective,
            skills_to_practice=day.skills_to_practice,
            learning_activities=day.learning_activities,
            interview_questions=day.interview_questions,
            practical_exercise=day.practical_exercise,
            estimated_duration_minutes=day.estimated_duration_minutes,
            completion_criteria=day.completion_criteria,
            tasks=tasks,
            day_completed=False,
        )
        stored.append(record.model_dump(mode="json"))
    return stored


async def generate_preparation_plan(
    user_id: str,
    payload: GeneratePreparationPlanRequest,
    resume_repo: ResumeRepository,
    analysis_repo: AnalysisRepository,
    job_match_repo: JobMatchRepository,
    interview_repo: InterviewRepository,
    plan_repo: PreparationPlanRepository,
) -> PreparationPlanResponse:
    resume = await resume_repo.find_by_id_for_user(payload.resume_id, user_id)
    if resume is None:
        raise PreparationPlanServiceError("Resume not found", status_code=404)

    analysis = await analysis_repo.find_latest_for_resume(user_id, payload.resume_id)
    if analysis is None or analysis.get("status") != "completed":
        raise PreparationPlanServiceError(
            "Analyse this resume before generating a 7-day plan.",
            status_code=422,
        )

    job_match = None
    if payload.job_match_id:
        job_match = await job_match_repo.find_by_id_for_user(payload.job_match_id, user_id)
        if job_match is None:
            raise PreparationPlanServiceError("Job match not found", status_code=404)
        if job_match.get("resume_id") != payload.resume_id:
            raise PreparationPlanServiceError(
                "Job match must belong to the selected resume.",
                status_code=422,
            )

    if payload.archive_plan_id:
        archived = await plan_repo.archive_plan(payload.archive_plan_id, user_id)
        if archived is None:
            raise PreparationPlanServiceError(
                "Plan to archive was not found or is not active.",
                status_code=404,
            )

    sessions = await interview_repo.list_completed_by_user(user_id, limit=8)
    evidence = build_preparation_plan_evidence(
        user_id=user_id,
        resume_id=payload.resume_id,
        job_match_id=payload.job_match_id,
        daily_study_minutes=payload.daily_study_minutes,
        resume_analysis=analysis,
        job_match=job_match,
        interview_sessions=sessions,
    )

    result = await asyncio.to_thread(run_preparation_plan_workflow, evidence)
    status = result.get("status")
    if status != "completed" or result.get("plan") is None:
        message = result.get("message") or "Plan generation failed."
        code = 422 if status == "insufficient_data" else 503
        raise PreparationPlanServiceError(message, status_code=code)

    gemini_plan = result["plan"]
    plan_start = datetime.now(timezone.utc).date()
    days = _gemini_days_to_stored(gemini_plan.days, plan_start)

    document = {
        "user_id": user_id,
        "resume_id": payload.resume_id,
        "job_match_id": payload.job_match_id,
        "status": "active",
        "daily_study_minutes": payload.daily_study_minutes,
        "model": get_gemini_model(),
        "plan_start_date": plan_start.isoformat(),
        "plan_summary": gemini_plan.plan_summary,
        "priority_gaps": gemini_plan.priority_gaps,
        "days": days,
    }

    try:
        saved = await plan_repo.create_plan(document)
    except PreparationPlanRepositoryError as exc:
        raise PreparationPlanServiceError(str(exc), status_code=500) from exc

    return _document_to_response(saved)


async def list_preparation_plans(
    user_id: str,
    plan_repo: PreparationPlanRepository,
) -> PreparationPlanListResponse:
    documents = await plan_repo.list_by_user(user_id)
    return PreparationPlanListResponse(
        plans=[_document_to_list_item(doc) for doc in documents]
    )


async def get_preparation_plan(
    user_id: str,
    plan_id: str,
    plan_repo: PreparationPlanRepository,
) -> PreparationPlanResponse:
    document = await plan_repo.find_by_id_for_user(plan_id, user_id)
    if document is None:
        raise PreparationPlanServiceError("Preparation plan not found", status_code=404)
    return _document_to_response(document)


async def update_task_completion(
    user_id: str,
    plan_id: str,
    day_number: int,
    task_id: str,
    payload: UpdatePlanTaskCompletionRequest,
    plan_repo: PreparationPlanRepository,
) -> PreparationPlanResponse:
    if day_number < 1 or day_number > 7:
        raise PreparationPlanServiceError("Invalid day number", status_code=422)

    try:
        updated = await plan_repo.update_task_completion(
            plan_id=plan_id,
            user_id=user_id,
            day_number=day_number,
            task_id=task_id,
            completed=payload.completed,
        )
    except PreparationPlanRepositoryError as exc:
        raise PreparationPlanServiceError(str(exc), status_code=500) from exc

    if updated is None:
        raise PreparationPlanServiceError("Plan or task not found", status_code=404)

    return _document_to_response(updated)


async def archive_preparation_plan(
    user_id: str,
    plan_id: str,
    plan_repo: PreparationPlanRepository,
) -> PreparationPlanResponse:
    archived = await plan_repo.archive_plan(plan_id, user_id)
    if archived is None:
        raise PreparationPlanServiceError(
            "Plan not found or already archived",
            status_code=404,
        )
    return _document_to_response(archived)


async def regenerate_preparation_plan(
    user_id: str,
    plan_id: str,
    resume_repo: ResumeRepository,
    analysis_repo: AnalysisRepository,
    job_match_repo: JobMatchRepository,
    interview_repo: InterviewRepository,
    plan_repo: PreparationPlanRepository,
) -> PreparationPlanResponse:
    existing = await plan_repo.find_by_id_for_user(plan_id, user_id)
    if existing is None:
        raise PreparationPlanServiceError("Preparation plan not found", status_code=404)

    request = GeneratePreparationPlanRequest(
        resume_id=existing["resume_id"],
        job_match_id=existing.get("job_match_id"),
        daily_study_minutes=existing.get("daily_study_minutes", 45),
        archive_plan_id=plan_id,
    )
    return await generate_preparation_plan(
        user_id=user_id,
        payload=request,
        resume_repo=resume_repo,
        analysis_repo=analysis_repo,
        job_match_repo=job_match_repo,
        interview_repo=interview_repo,
        plan_repo=plan_repo,
    )
