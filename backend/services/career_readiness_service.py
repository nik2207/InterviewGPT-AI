from collections import Counter
from datetime import datetime, timezone

from bson import ObjectId

from repositories.analysis_repository import AnalysisRepository
from repositories.career_readiness_repository import (
    CareerReadinessRepository,
    CareerReadinessRepositoryError,
)
from repositories.interview_repository import InterviewRepository
from repositories.job_match_repository import JobMatchRepository
from repositories.preparation_plan_repository import PreparationPlanRepository
from repositories.resume_repository import ResumeRepository
from schemas.career_readiness_schema import (
    SPEECH_DISCLAIMER,
    OverallReadinessIndicator,
    CareerReadinessReportListItem,
    CareerReadinessReportListResponse,
    CareerReadinessReportResponse,
    CommunicationIndicatorsSection,
    ComponentScoreSection,
    DataCoverageItem,
    DataCoverageSummary,
    GenerateCareerReadinessRequest,
    InterviewTrendPoint,
    PreparationPlanSummarySection,
)
from services.career_readiness_scoring import (
    collect_dimension_scores,
    collect_session_scores,
    compute_overall_readiness,
    dimension_to_percent,
    get_scoring_rules,
    make_component,
)
from services.preparation_plan_service import _progress


class CareerReadinessServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _progress_from_plan(document: dict) -> tuple[float, int, int]:
    return _progress(document.get("days") or [])


def _collect_speech_metrics(sessions: list[dict]) -> CommunicationIndicatorsSection:
    wpm_values: list[float] = []
    filler_values: list[float] = []
    count = 0
    for session in sessions:
        for answer in session.get("answers", []):
            metrics = answer.get("speech_metrics")
            if not metrics or metrics.get("input_mode") == "typed":
                continue
            count += 1
            wpm = metrics.get("words_per_minute")
            if wpm is not None:
                wpm_values.append(float(wpm))
            filler = metrics.get("filler_word_count")
            if filler is not None:
                filler_values.append(float(filler))

    if count == 0:
        return CommunicationIndicatorsSection(
            status="insufficient_data",
            speech_answer_count=0,
            detail="No speech-based answers with timing metrics yet.",
        )

    avg_wpm = round(sum(wpm_values) / len(wpm_values), 1) if wpm_values else None
    avg_filler = round(sum(filler_values) / len(filler_values), 1) if filler_values else None
    return CommunicationIndicatorsSection(
        status="available",
        speech_answer_count=count,
        average_words_per_minute=avg_wpm,
        average_filler_words=avg_filler,
        disclaimer=SPEECH_DISCLAIMER,
        detail="Descriptive pacing and filler-word averages from saved speech answers.",
    )


def _build_recommended_actions(
    *,
    has_interviews: bool,
    has_job_match: bool,
    has_plan: bool,
    plan_progress: float | None,
    weakest_label: str | None,
    alignment_score: float | None,
) -> list[str]:
    actions: list[str] = []
    if not has_interviews:
        actions.append("Complete at least one mock interview to unlock readiness scoring.")
    if not has_job_match:
        actions.append("Run a job description match to add resume–role alignment to your report.")
    if alignment_score is not None and alignment_score < 60:
        actions.append("Close resume gaps highlighted in your job match before the next interview.")
    if weakest_label:
        actions.append(f"Focus your next practice session on improving {weakest_label}.")
    if has_plan and plan_progress is not None and plan_progress < 100:
        actions.append("Continue your 7-day preparation plan — check off today's tasks.")
    elif not has_plan:
        actions.append("Generate a 7-day preparation plan from the career workspace.")
    if has_interviews and len(actions) < 3:
        actions.append("Review answer improvement coach feedback on your lowest-scoring question.")
    return actions[:8]


def _strongest_and_weakest(
    sessions: list[dict],
    resume_analysis: dict | None,
    job_match: dict | None,
) -> tuple[list[str], list[str]]:
    strength_counter: Counter[str] = Counter()
    gap_counter: Counter[str] = Counter()

    for session in sessions:
        for answer in session.get("answers", []):
            if answer.get("evaluation_status") != "evaluated":
                continue
            evaluation = answer.get("evaluation") or {}
            for s in evaluation.get("strengths") or []:
                strength_counter[str(s)[:120]] += 1
            for g in evaluation.get("missing_concepts") or []:
                gap_counter[str(g)[:120]] += 1

    if resume_analysis:
        analysis = resume_analysis.get("analysis") or {}
        for skill in (analysis.get("strengths") or analysis.get("skills") or [])[:5]:
            strength_counter[str(skill)[:80]] += 1
        for gap in (analysis.get("skill_gaps") or analysis.get("areas_to_improve") or [])[:5]:
            gap_counter[str(gap)[:80]] += 1

    if job_match:
        for item in job_match.get("skill_alignments") or []:
            if item.get("match_status") == "matched" and item.get("skill"):
                strength_counter[str(item["skill"])[:80]] += 1
            elif item.get("match_status") != "matched" and item.get("skill"):
                gap_counter[str(item["skill"])[:80]] += 1

    strongest = [label for label, _ in strength_counter.most_common(8)]
    gaps = [label for label, _ in gap_counter.most_common(8)]
    return strongest, gaps


def _weakest_dimension_label(dims: dict[str, list[int]]) -> str | None:
    averages: list[tuple[str, float]] = []
    labels = {
        "technical_correctness": "technical knowledge",
        "relevance": "answer relevance",
        "completeness": "answer completeness",
        "answer_structure": "answer structure",
    }
    for key, values in dims.items():
        if values:
            averages.append((labels.get(key, key), sum(values) / len(values)))
    if not averages:
        return None
    weakest = min(averages, key=lambda item: item[1])
    return weakest[0]


async def build_career_readiness_report(
    user_id: str,
    payload: GenerateCareerReadinessRequest,
    resume_repo: ResumeRepository,
    analysis_repo: AnalysisRepository,
    job_match_repo: JobMatchRepository,
    interview_repo: InterviewRepository,
    plan_repo: PreparationPlanRepository,
) -> CareerReadinessReportResponse:
    resume = await resume_repo.find_by_id_for_user(payload.resume_id, user_id)
    if resume is None:
        raise CareerReadinessServiceError("Resume not found", status_code=404)

    analysis = await analysis_repo.find_latest_for_resume(user_id, payload.resume_id)

    job_match = None
    if payload.job_match_id:
        job_match = await job_match_repo.find_by_id_for_user(payload.job_match_id, user_id)
        if job_match is None:
            raise CareerReadinessServiceError("Job match not found", status_code=404)
        if job_match.get("resume_id") != payload.resume_id:
            raise CareerReadinessServiceError(
                "Job match must belong to the selected resume.",
                status_code=422,
            )

    sessions = await interview_repo.list_completed_by_user(user_id, limit=25)

    plans = await plan_repo.list_by_user(user_id, limit=10)
    active_plan = None
    for plan in plans:
        if plan.get("status") != "active":
            continue
        if plan.get("resume_id") != payload.resume_id:
            continue
        if payload.job_match_id and plan.get("job_match_id") != payload.job_match_id:
            continue
        active_plan = plan
        break
    if active_plan is None:
        for plan in plans:
            if plan.get("resume_id") == payload.resume_id:
                active_plan = plan
                break

    target_role = "Interview preparation"
    if job_match:
        target_role = job_match.get("job_title") or target_role
    elif analysis:
        recs = (analysis.get("analysis") or {}).get("role_recommendations") or []
        if recs:
            target_role = str(recs[0])[:200]

    now = datetime.now(timezone.utc)
    coverage: list[DataCoverageItem] = [
        DataCoverageItem(
            source="resume_analysis",
            available=analysis is not None and analysis.get("status") == "completed",
            detail="Resume skills and gaps" if analysis else "No saved resume analysis",
            last_updated=analysis.get("updated_at") if analysis else None,
        ),
        DataCoverageItem(
            source="job_match",
            available=job_match is not None,
            detail="Resume–JD alignment" if job_match else "No job match selected",
            last_updated=job_match.get("updated_at") if job_match else None,
        ),
        DataCoverageItem(
            source="interview_sessions",
            available=len(sessions) > 0,
            detail=f"{len(sessions)} completed interview(s)",
            last_updated=sessions[0].get("completed_at") if sessions else None,
        ),
        DataCoverageItem(
            source="preparation_plan",
            available=active_plan is not None,
            detail="7-day plan progress" if active_plan else "No preparation plan",
            last_updated=active_plan.get("updated_at") if active_plan else None,
        ),
    ]

    dims = collect_dimension_scores(sessions)
    session_scores = collect_session_scores(sessions)

    alignment_score = None
    if job_match:
        alignment_score = float((job_match.get("score") or {}).get("match_score", 0))

    technical = dimension_to_percent(dims["technical_correctness"])
    relevance = dimension_to_percent(dims["relevance"])
    completeness = dimension_to_percent(dims["completeness"])
    structure = dimension_to_percent(dims["answer_structure"])
    interview_perf = (
        round(sum(session_scores) / len(session_scores), 1) if session_scores else None
    )

    prep_progress = None
    prep_section = None
    if active_plan:
        progress, completed, total = _progress_from_plan(active_plan)
        prep_progress = progress
        plan_id = active_plan["_id"]
        if isinstance(plan_id, ObjectId):
            plan_id = str(plan_id)
        prep_section = PreparationPlanSummarySection(
            plan_id=str(plan_id),
            status=active_plan.get("status", "active"),
            progress_percent=progress,
            tasks_completed=completed,
            tasks_total=total,
            last_updated=active_plan.get("updated_at", now),
        )

    overall = compute_overall_readiness(
        alignment=alignment_score,
        technical=technical,
        relevance=relevance,
        completeness=completeness,
        structure=structure,
        interview_performance=interview_perf,
        preparation=prep_progress,
    )

    strongest, gaps = _strongest_and_weakest(sessions, analysis, job_match)
    weakest = _weakest_dimension_label(dims)
    communication = _collect_speech_metrics(sessions)

    trends = []
    for session in sessions[:10]:
        sid = session["_id"]
        if isinstance(sid, ObjectId):
            sid = str(sid)
        summary = session.get("summary") or {}
        trends.append(
            InterviewTrendPoint(
                session_id=str(sid),
                role=session.get("role", "Interview"),
                completed_at=session.get("completed_at") or session.get("updated_at") or now,
                overall_score=summary.get("average_score"),
            )
        )

    actions = _build_recommended_actions(
        has_interviews=len(sessions) > 0,
        has_job_match=job_match is not None,
        has_plan=active_plan is not None,
        plan_progress=prep_progress,
        weakest_label=weakest,
        alignment_score=alignment_score,
    )

    return CareerReadinessReportResponse(
        id="pending",
        user_id=user_id,
        resume_id=payload.resume_id,
        job_match_id=payload.job_match_id,
        target_role=target_role,
        generated_at=now,
        data_coverage=DataCoverageSummary(
            items=coverage,
            summary=f"{sum(1 for c in coverage if c.available)} of {len(coverage)} data sources available.",
        ),
        overall_readiness=overall,
        resume_job_alignment=make_component(
            alignment_score,
            detail=(
                "From saved job match weighted score."
                if alignment_score is not None
                else "Select a job match for alignment scoring."
            ),
            sample_size=1 if alignment_score is not None else 0,
        ),
        technical_knowledge=make_component(
            technical,
            detail=(
                f"From {len(dims['technical_correctness'])} evaluated answer(s)."
                if technical
                else "Not enough practice data."
            ),
            sample_size=len(dims["technical_correctness"]),
        ),
        answer_relevance=make_component(
            relevance,
            detail=f"From {len(dims['relevance'])} evaluated answer(s).",
            sample_size=len(dims["relevance"]),
        ),
        answer_completeness=make_component(
            completeness,
            detail=f"From {len(dims['completeness'])} evaluated answer(s).",
            sample_size=len(dims["completeness"]),
        ),
        answer_structure=make_component(
            structure,
            detail=f"From {len(dims['answer_structure'])} evaluated answer(s).",
            sample_size=len(dims["answer_structure"]),
        ),
        communication_indicators=communication,
        strongest_skills=strongest,
        skills_requiring_improvement=gaps,
        interview_performance_trends=trends,
        preparation_plan=prep_section,
        recommended_next_actions=actions,
        scoring_rules=get_scoring_rules(),
    )


def _document_to_response(document: dict) -> CareerReadinessReportResponse:
    report_id = document["_id"]
    if isinstance(report_id, ObjectId):
        report_id = str(report_id)

    prep = document.get("preparation_plan")

    return CareerReadinessReportResponse(
        id=str(report_id),
        user_id=document["user_id"],
        resume_id=document["resume_id"],
        job_match_id=document.get("job_match_id"),
        target_role=document.get("target_role", ""),
        generated_at=document["generated_at"],
        data_coverage=DataCoverageSummary.model_validate(document["data_coverage"]),
        overall_readiness=OverallReadinessIndicator.model_validate(
            document["overall_readiness"]
        ),
        resume_job_alignment=ComponentScoreSection.model_validate(
            document["resume_job_alignment"]
        ),
        technical_knowledge=ComponentScoreSection.model_validate(
            document["technical_knowledge"]
        ),
        answer_relevance=ComponentScoreSection.model_validate(document["answer_relevance"]),
        answer_completeness=ComponentScoreSection.model_validate(
            document["answer_completeness"]
        ),
        answer_structure=ComponentScoreSection.model_validate(document["answer_structure"]),
        communication_indicators=CommunicationIndicatorsSection.model_validate(
            document["communication_indicators"]
        ),
        strongest_skills=document.get("strongest_skills", []),
        skills_requiring_improvement=document.get("skills_requiring_improvement", []),
        interview_performance_trends=[
            InterviewTrendPoint.model_validate(item)
            for item in document.get("interview_performance_trends", [])
        ],
        preparation_plan=(
            PreparationPlanSummarySection.model_validate(prep) if prep else None
        ),
        recommended_next_actions=document.get("recommended_next_actions", []),
        scoring_rules=document.get("scoring_rules", get_scoring_rules()),
    )


async def generate_and_save_report(
    user_id: str,
    payload: GenerateCareerReadinessRequest,
    resume_repo: ResumeRepository,
    analysis_repo: AnalysisRepository,
    job_match_repo: JobMatchRepository,
    interview_repo: InterviewRepository,
    plan_repo: PreparationPlanRepository,
    readiness_repo: CareerReadinessRepository,
) -> CareerReadinessReportResponse:
    report = await build_career_readiness_report(
        user_id=user_id,
        payload=payload,
        resume_repo=resume_repo,
        analysis_repo=analysis_repo,
        job_match_repo=job_match_repo,
        interview_repo=interview_repo,
        plan_repo=plan_repo,
    )
    to_store = report.model_dump(mode="json")
    to_store.pop("id", None)
    to_store["user_id"] = user_id
    try:
        saved = await readiness_repo.create_report(to_store)
    except CareerReadinessRepositoryError as exc:
        raise CareerReadinessServiceError(str(exc), status_code=500) from exc
    return _document_to_response(saved)


async def get_saved_report(
    user_id: str,
    report_id: str,
    readiness_repo: CareerReadinessRepository,
) -> CareerReadinessReportResponse:
    document = await readiness_repo.find_by_id_for_user(report_id, user_id)
    if document is None:
        raise CareerReadinessServiceError("Readiness report not found", status_code=404)
    return _document_to_response(document)


async def list_reports(
    user_id: str,
    readiness_repo: CareerReadinessRepository,
) -> CareerReadinessReportListResponse:
    documents = await readiness_repo.list_by_user(user_id)
    items: list[CareerReadinessReportListItem] = []
    for doc in documents:
        rid = doc["_id"]
        if isinstance(rid, ObjectId):
            rid = str(rid)
        overall = doc.get("overall_readiness") or {}
        items.append(
            CareerReadinessReportListItem(
                id=str(rid),
                resume_id=doc["resume_id"],
                job_match_id=doc.get("job_match_id"),
                target_role=doc.get("target_role", ""),
                overall_score=overall.get("score"),
                overall_status=overall.get("status", "insufficient_data"),
                generated_at=doc["generated_at"],
            )
        )
    return CareerReadinessReportListResponse(reports=items)
