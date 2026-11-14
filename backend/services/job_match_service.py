from bson import ObjectId

from repositories.analysis_repository import AnalysisRepository
from repositories.job_match_repository import JobMatchRepository, JobMatchRepositoryError
from repositories.resume_repository import ResumeRepository
from schemas.analysis_schema import InterviewQuestionResponse
from schemas.job_match_schema import (
    CreateJobMatchRequest,
    JobMatchListItem,
    JobMatchListResponse,
    JobMatchResponse,
)
from services.gemini_config import GeminiConfigurationError, get_gemini_model
from services.gemini_job_match_service import (
    JobMatchGeminiError,
    JobMatchGeminiUnavailableError,
    analyze_job_match_with_gemini,
)
from services.job_match_score_service import compute_job_match_score


class JobMatchServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _excerpt(text: str, limit: int = 240) -> str:
    trimmed = text.strip()
    if len(trimmed) <= limit:
        return trimmed
    return trimmed[: limit - 1] + "…"


def _document_to_response(document: dict) -> JobMatchResponse:
    analysis_id = document["_id"]
    if isinstance(analysis_id, ObjectId):
        analysis_id = str(analysis_id)

    questions = [
        InterviewQuestionResponse.model_validate(item)
        for item in document.get("interview_questions", [])
    ]
    from schemas.job_match_schema import JobMatchScoreBreakdown, SkillAlignmentItem

    return JobMatchResponse(
        id=str(analysis_id),
        user_id=document["user_id"],
        resume_id=document["resume_id"],
        job_title=document.get("job_title") or document.get("job_title_inferred", "Role"),
        status=document["status"],
        model=document.get("model", ""),
        created_at=document["created_at"],
        updated_at=document["updated_at"],
        job_description_excerpt=document.get("job_description_excerpt", ""),
        required_skills=document.get("required_skills", []),
        preferred_skills=document.get("preferred_skills", []),
        skill_alignments=[
            SkillAlignmentItem.model_validate(item)
            for item in document.get("skill_alignments", [])
        ],
        score=JobMatchScoreBreakdown.model_validate(document["score"]),
        gap_summary=document.get("gap_summary", ""),
        strengths_for_role=document.get("strengths_for_role", []),
        interview_questions=questions,
        error_message=document.get("error_message"),
    )


def _document_to_list_item(document: dict) -> JobMatchListItem:
    match_id = document["_id"]
    if isinstance(match_id, ObjectId):
        match_id = str(match_id)
    score_doc = document.get("score") or {}
    return JobMatchListItem(
        id=str(match_id),
        resume_id=document["resume_id"],
        job_title=document.get("job_title") or "Role",
        match_score=float(score_doc.get("match_score", 0)),
        status=document.get("status", "completed"),
        created_at=document["created_at"],
    )


async def create_job_match(
    user_id: str,
    payload: CreateJobMatchRequest,
    resume_repo: ResumeRepository,
    analysis_repo: AnalysisRepository,
    job_match_repo: JobMatchRepository,
) -> JobMatchResponse:
    resume = await resume_repo.find_by_id_for_user(payload.resume_id, user_id)
    if resume is None:
        raise JobMatchServiceError("Resume not found", status_code=404)

    analysis_doc = await analysis_repo.find_latest_for_resume(user_id, payload.resume_id)
    if analysis_doc is None or analysis_doc.get("status") != "completed":
        raise JobMatchServiceError(
            "Analyse this resume before running job match.",
            status_code=422,
        )

    extracted_text = (resume.get("extracted_text") or "").strip()
    if not extracted_text:
        raise JobMatchServiceError(
            "Resume text is not available for job match.",
            status_code=422,
        )

    analysis_data = analysis_doc.get("analysis") or {}
    summary = (analysis_data.get("professional_summary") or "").strip()
    skills = list(analysis_data.get("skills") or [])
    experience = (analysis_data.get("experience_analysis") or "")[:2000]
    analysis_summary = f"{summary}\n\nExperience:\n{experience}"

    try:
        gemini_payload = analyze_job_match_with_gemini(
            resume_text=extracted_text,
            analysis_summary=analysis_summary,
            skills=skills,
            job_description=payload.job_description.strip(),
        )
    except GeminiConfigurationError as exc:
        raise JobMatchServiceError(str(exc), status_code=503) from exc
    except JobMatchGeminiUnavailableError as exc:
        raise JobMatchServiceError(str(exc), status_code=503) from exc
    except JobMatchGeminiError as exc:
        raise JobMatchServiceError(str(exc), status_code=502) from exc

    score = compute_job_match_score(gemini_payload.skill_alignments)
    job_title = (
        payload.job_title.strip()
        if payload.job_title and payload.job_title.strip()
        else gemini_payload.job_title_inferred
    )
    questions = [q.model_dump() for q in gemini_payload.interview_questions]

    document = {
        "user_id": user_id,
        "resume_id": payload.resume_id,
        "resume_analysis_id": str(analysis_doc["_id"]),
        "job_title": job_title,
        "job_title_inferred": gemini_payload.job_title_inferred,
        "job_description_excerpt": _excerpt(payload.job_description),
        "job_description_length": len(payload.job_description.strip()),
        "status": "completed",
        "model": get_gemini_model(),
        "required_skills": gemini_payload.required_skills,
        "preferred_skills": gemini_payload.preferred_skills,
        "skill_alignments": [item.model_dump() for item in gemini_payload.skill_alignments],
        "score": score.model_dump(),
        "gap_summary": gemini_payload.gap_summary,
        "strengths_for_role": gemini_payload.strengths_for_role,
        "interview_questions": questions,
        "error_message": None,
    }

    try:
        saved = await job_match_repo.create_match(document)
    except JobMatchRepositoryError as exc:
        raise JobMatchServiceError(str(exc), status_code=500) from exc

    return _document_to_response(saved)


async def list_job_matches(
    user_id: str,
    job_match_repo: JobMatchRepository,
) -> JobMatchListResponse:
    documents = await job_match_repo.list_by_user(user_id)
    return JobMatchListResponse(
        matches=[_document_to_list_item(doc) for doc in documents]
    )


async def get_job_match(
    user_id: str,
    match_id: str,
    job_match_repo: JobMatchRepository,
) -> JobMatchResponse:
    document = await job_match_repo.find_by_id_for_user(match_id, user_id)
    if document is None:
        raise JobMatchServiceError("Job match not found", status_code=404)
    return _document_to_response(document)
