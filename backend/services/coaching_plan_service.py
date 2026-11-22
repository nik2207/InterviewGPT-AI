import asyncio
from datetime import datetime, timezone

from repositories.analysis_repository import AnalysisRepository
from repositories.interview_repository import InterviewRepository
from schemas.coaching_schema import CoachingPlanResponse
from services.coaching_evidence_service import build_evidence_bundle
from workflows.coaching_plan_graph import run_coaching_plan_workflow


class CoachingPlanServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


async def generate_coaching_plan_for_session(
    user_id: str,
    session_id: str,
    interview_repo: InterviewRepository,
    analysis_repo: AnalysisRepository,
) -> CoachingPlanResponse:
    session = await interview_repo.find_by_id_for_user(session_id, user_id)
    if session is None:
        raise CoachingPlanServiceError("Interview session not found", status_code=404)
    if session.get("status") != "completed":
        raise CoachingPlanServiceError(
            "Coaching plan is available for completed interviews only.",
            status_code=422,
        )

    resume_analysis = None
    resume_id = session.get("resume_id")
    if resume_id:
        resume_analysis = await analysis_repo.find_latest_for_resume(user_id, resume_id)

    history = await interview_repo.list_completed_by_user(user_id, limit=5)
    evidence = build_evidence_bundle(
        user_id=user_id,
        session_id=session_id,
        session=session,
        resume_analysis=resume_analysis,
        history_sessions=history,
    )

    result = await asyncio.to_thread(run_coaching_plan_workflow, evidence)
    status = result.get("status", "generation_failed")
    plan = result.get("plan")

    return CoachingPlanResponse(
        session_id=session_id,
        status=status,
        generated_at=datetime.now(timezone.utc),
        evidence_count=len(evidence.items) if evidence else 0,
        plan=plan,
        message=result.get("message"),
    )
