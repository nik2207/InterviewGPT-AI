from datetime import date, datetime, timezone
from uuid import uuid4

from bson import ObjectId

from repositories.analysis_repository import AnalysisRepository
from repositories.interview_repository import InterviewRepository
from repositories.job_application_repository import (
    JobApplicationDuplicateError,
    JobApplicationRepository,
    JobApplicationRepositoryError,
)
from repositories.job_match_repository import JobMatchRepository
from repositories.resume_repository import ResumeRepository
from schemas.interview_schema import CreateInterviewSessionRequest, CustomInterviewQuestionInput
from schemas.job_application_schema import (
    CreateJobApplicationRequest,
    JobApplicationListResponse,
    JobApplicationResponse,
    JobApplicationStatsResponse,
    StartApplicationPracticeRequest,
    StartApplicationPracticeResponse,
    UpdateJobApplicationRequest,
)
from services.interview_service import InterviewServiceError, create_interview_session


class JobApplicationServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _oid_str(value) -> str:
    if isinstance(value, ObjectId):
        return str(value)
    return str(value)


def _serialize_dates_for_mongo(data: dict) -> dict:
    result = dict(data)
    for key in ("application_date", "follow_up_date"):
        if key in result and isinstance(result[key], date):
            result[key] = datetime.combine(
                result[key], datetime.min.time(), tzinfo=timezone.utc
            )
    return result


def _read_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _to_response(document: dict) -> JobApplicationResponse:
    return JobApplicationResponse(
        id=_oid_str(document["_id"]),
        user_id=document["user_id"],
        company=document["company"],
        job_title=document["job_title"],
        job_description=document.get("job_description", ""),
        job_posting_url=document.get("job_posting_url"),
        location=document.get("location", ""),
        employment_type=document.get("employment_type", "full_time"),
        application_date=_read_date(document.get("application_date")),
        status=document.get("status", "interested"),
        resume_id=document.get("resume_id"),
        job_match_id=document.get("job_match_id"),
        interview_dates=document.get("interview_dates", []),
        notes=document.get("notes", ""),
        follow_up_date=_read_date(document.get("follow_up_date")),
        interview_session_id=document.get("interview_session_id"),
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


async def create_job_application(
    user_id: str,
    payload: CreateJobApplicationRequest,
    repo: JobApplicationRepository,
) -> JobApplicationResponse:
    interview_dates = [entry.model_dump() for entry in payload.interview_dates]
    for entry in interview_dates:
        if not entry.get("id"):
            entry["id"] = uuid4().hex[:12]

    document = _serialize_dates_for_mongo(
        {
            "user_id": user_id,
            "company": payload.company.strip(),
            "job_title": payload.job_title.strip(),
            "job_description": payload.job_description.strip(),
            "job_posting_url": payload.job_posting_url,
            "location": payload.location.strip(),
            "employment_type": payload.employment_type,
            "application_date": payload.application_date,
            "status": payload.status,
            "resume_id": payload.resume_id,
            "job_match_id": payload.job_match_id,
            "interview_dates": interview_dates,
            "notes": payload.notes.strip(),
            "follow_up_date": payload.follow_up_date,
            "interview_session_id": None,
        }
    )

    try:
        saved = await repo.create_application(document)
    except JobApplicationDuplicateError as exc:
        raise JobApplicationServiceError(str(exc), status_code=409) from exc
    except JobApplicationRepositoryError:
        raise JobApplicationServiceError("Unable to save application.", status_code=500) from None

    return _to_response(saved)


async def list_job_applications(
    user_id: str,
    repo: JobApplicationRepository,
    *,
    status: str | None,
    search: str | None,
    employment_type: str | None,
    page: int,
    page_size: int,
    sort_by: str,
    sort_dir: int,
) -> JobApplicationListResponse:
    items, total = await repo.list_applications(
        user_id,
        status=status,
        search=search,
        employment_type=employment_type,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return JobApplicationListResponse(
        items=[_to_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_job_application(
    user_id: str,
    app_id: str,
    repo: JobApplicationRepository,
) -> JobApplicationResponse:
    document = await repo.find_by_id_for_user(app_id, user_id)
    if document is None:
        raise JobApplicationServiceError("Application not found.", status_code=404)
    return _to_response(document)


async def update_job_application(
    user_id: str,
    app_id: str,
    payload: UpdateJobApplicationRequest,
    repo: JobApplicationRepository,
) -> JobApplicationResponse:
    document = await repo.find_by_id_for_user(app_id, user_id)
    if document is None:
        raise JobApplicationServiceError("Application not found.", status_code=404)

    update_fields = payload.model_dump(exclude_unset=True)
    if "interview_dates" in update_fields and update_fields["interview_dates"] is not None:
        update_fields["interview_dates"] = [
            entry if isinstance(entry, dict) else entry.model_dump()
            for entry in update_fields["interview_dates"]
        ]
    update_fields = _serialize_dates_for_mongo(update_fields)

    if not update_fields:
        return _to_response(document)

    try:
        updated = await repo.update_application(app_id, user_id, update_fields)
    except JobApplicationDuplicateError as exc:
        raise JobApplicationServiceError(str(exc), status_code=409) from exc
    except JobApplicationRepositoryError:
        raise JobApplicationServiceError("Unable to update application.", status_code=500) from None

    if updated is None:
        raise JobApplicationServiceError("Application not found.", status_code=404)
    return _to_response(updated)


async def delete_job_application(
    user_id: str,
    app_id: str,
    repo: JobApplicationRepository,
) -> None:
    try:
        deleted = await repo.delete_application(app_id, user_id)
    except JobApplicationRepositoryError:
        raise JobApplicationServiceError("Unable to delete application.", status_code=500) from None
    if not deleted:
        raise JobApplicationServiceError("Application not found.", status_code=404)


async def job_application_stats(
    user_id: str,
    repo: JobApplicationRepository,
) -> JobApplicationStatsResponse:
    documents = await repo.list_all_for_user(user_id)
    by_status: dict[str, int] = {}
    upcoming_interviews: list[dict] = []
    upcoming_follow_ups: list[dict] = []
    now = datetime.now(timezone.utc)
    today = now.date()

    for doc in documents:
        status = doc.get("status", "interested")
        by_status[status] = by_status.get(status, 0) + 1

        for entry in doc.get("interview_dates", []):
            sched = entry.get("scheduled_at")
            if isinstance(sched, datetime) and sched >= now:
                upcoming_interviews.append(
                    {
                        "application_id": _oid_str(doc["_id"]),
                        "company": doc["company"],
                        "job_title": doc["job_title"],
                        "label": entry.get("label"),
                        "scheduled_at": sched.isoformat(),
                    }
                )

        follow = _read_date(doc.get("follow_up_date"))
        if follow and follow >= today:
            upcoming_follow_ups.append(
                {
                    "application_id": _oid_str(doc["_id"]),
                    "company": doc["company"],
                    "job_title": doc["job_title"],
                    "follow_up_date": follow.isoformat(),
                }
            )

    upcoming_interviews.sort(key=lambda item: item["scheduled_at"])
    upcoming_follow_ups.sort(key=lambda item: item["follow_up_date"])

    return JobApplicationStatsResponse(
        total=len(documents),
        by_status=by_status,
        upcoming_interviews=upcoming_interviews[:20],
        upcoming_follow_ups=upcoming_follow_ups[:20],
    )


async def start_application_practice(
    user_id: str,
    app_id: str,
    payload: StartApplicationPracticeRequest,
    app_repo: JobApplicationRepository,
    interview_repo: InterviewRepository,
    resume_repo: ResumeRepository,
    job_match_repo: JobMatchRepository,
    analysis_repo: AnalysisRepository,
) -> StartApplicationPracticeResponse:
    document = await app_repo.find_by_id_for_user(app_id, user_id)
    if document is None:
        raise JobApplicationServiceError("Application not found.", status_code=404)

    resume_id = payload.resume_id or document.get("resume_id")
    custom_questions: list[CustomInterviewQuestionInput] = []

    match_id = document.get("job_match_id")
    if match_id:
        match = await job_match_repo.find_by_id_for_user(match_id, user_id)
        if match and match.get("interview_questions"):
            for item in match["interview_questions"][: payload.question_count]:
                custom_questions.append(
                    CustomInterviewQuestionInput(
                        question=item["question"],
                        category=item.get("category", "role_fit"),
                        difficulty=item.get("difficulty", "intermediate"),
                        relevance=item.get("relevance", document["company"]),
                        evaluates=item.get("evaluates", "Role fit"),
                    )
                )

    if len(custom_questions) < 3:
        jd = (document.get("job_description") or "")[:2000]
        role = f"{document['job_title']} at {document['company']}"
        seeds = [
            f"Why are you interested in the {role} role?",
            f"How does your experience relate to this role? Context: {jd[:400] or 'See job description on file.'}",
            "Describe a relevant project or achievement for this application.",
        ]
        for text in seeds[: max(3, payload.question_count)]:
            custom_questions.append(
                CustomInterviewQuestionInput(
                    question=text[:500],
                    category="behavioral" if "interested" in text.lower() else "technical",
                    difficulty="intermediate",
                    relevance=document["company"],
                    evaluates="Role fit",
                )
            )

    create_payload = CreateInterviewSessionRequest(
        role=f"{document['job_title']} — {document['company']}",
        difficulty="intermediate",
        interview_type="mixed",
        resume_id=resume_id,
        question_count=min(payload.question_count, len(custom_questions)),
        custom_questions=custom_questions[: payload.question_count],
        voice_interview_enabled=payload.voice_interview_enabled,
    )

    try:
        session = await create_interview_session(
            user_id=user_id,
            payload=create_payload,
            interview_repo=interview_repo,
            resume_repo=resume_repo,
            analysis_repo=analysis_repo,
        )
    except InterviewServiceError as exc:
        raise JobApplicationServiceError(str(exc), status_code=exc.status_code) from exc

    await app_repo.link_interview_session(app_id, user_id, session.id)

    return StartApplicationPracticeResponse(
        application_id=app_id,
        interview_session_id=session.id,
    )
