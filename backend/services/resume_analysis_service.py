from repositories.analysis_repository import AnalysisRepository, AnalysisRepositoryError
from repositories.resume_repository import ResumeRepository
from schemas.analysis_schema import (
    InterviewQuestionResponse,
    ResumeAnalysisResponse,
    ResumeAnalysisSectionsResponse,
)
from services.gemini_config import GeminiConfigurationError
from services.gemini_resume_analysis_service import (
    GeminiAuthError,
    GeminiRateLimitError,
    GeminiResponseError,
    GeminiServiceError,
    GeminiUnavailableError,
    analyze_resume_text,
)


class ResumeAnalysisServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _document_to_response(document: dict, cached: bool = False) -> ResumeAnalysisResponse:
    from bson import ObjectId

    analysis_id = document["_id"]
    if isinstance(analysis_id, ObjectId):
        analysis_id = str(analysis_id)

    analysis_data = document["analysis"]
    questions = document.get("interview_questions", [])

    return ResumeAnalysisResponse(
        id=str(analysis_id),
        resume_id=document["resume_id"],
        user_id=document["user_id"],
        status=document["status"],
        model=document["model"],
        created_at=document["created_at"],
        updated_at=document["updated_at"],
        analysis=ResumeAnalysisSectionsResponse.model_validate(analysis_data),
        interview_questions=[
            InterviewQuestionResponse.model_validate(item) for item in questions
        ],
        cached=cached,
    )


def _split_analysis_payload(payload) -> tuple[dict, list[dict]]:
    analysis = payload.analysis
    questions = [question.model_dump() for question in analysis.interview_questions]
    analysis_dict = analysis.model_dump()
    analysis_dict.pop("interview_questions", None)
    return analysis_dict, questions


async def get_saved_analysis(
    user_id: str,
    resume_id: str,
    resume_repo: ResumeRepository,
    analysis_repo: AnalysisRepository,
) -> ResumeAnalysisResponse:
    resume = await resume_repo.find_by_id_for_user(resume_id, user_id)
    if resume is None:
        raise ResumeAnalysisServiceError("Resume not found", status_code=404)

    document = await analysis_repo.find_latest_for_resume(user_id, resume_id)
    if document is None:
        raise ResumeAnalysisServiceError(
            "No analysis found for this resume.",
            status_code=404,
        )

    return _document_to_response(document)


async def analyze_resume(
    user_id: str,
    resume_id: str,
    resume_repo: ResumeRepository,
    analysis_repo: AnalysisRepository,
    refresh: bool = False,
) -> ResumeAnalysisResponse:
    resume = await resume_repo.find_by_id_for_user(resume_id, user_id)
    if resume is None:
        raise ResumeAnalysisServiceError("Resume not found", status_code=404)

    extracted_text = (resume.get("extracted_text") or "").strip()
    if not extracted_text:
        raise ResumeAnalysisServiceError(
            "Resume text is not available for analysis.",
            status_code=422,
        )

    content_sha256 = resume.get("content_sha256", "")
    if not refresh:
        cached = await analysis_repo.find_latest_matching_content(
            user_id=user_id,
            resume_id=resume_id,
            content_sha256=content_sha256,
        )
        if cached is not None:
            return _document_to_response(cached, cached=True)

    try:
        gemini_result = analyze_resume_text(extracted_text)
    except GeminiConfigurationError as exc:
        raise ResumeAnalysisServiceError(str(exc), status_code=503) from exc
    except GeminiAuthError as exc:
        raise ResumeAnalysisServiceError(str(exc), status_code=503) from exc
    except GeminiRateLimitError as exc:
        raise ResumeAnalysisServiceError(str(exc), status_code=429) from exc
    except GeminiUnavailableError as exc:
        raise ResumeAnalysisServiceError(str(exc), status_code=503) from exc
    except GeminiResponseError as exc:
        raise ResumeAnalysisServiceError(str(exc), status_code=502) from exc
    except GeminiServiceError as exc:
        raise ResumeAnalysisServiceError(str(exc), status_code=502) from exc

    analysis_dict, questions = _split_analysis_payload(gemini_result)

    from services.gemini_config import get_gemini_model

    try:
        saved = await analysis_repo.create_analysis(
            user_id=user_id,
            resume_id=resume_id,
            content_sha256=content_sha256,
            model=get_gemini_model(),
            analysis=analysis_dict,
            interview_questions=questions,
            status="completed",
        )
    except AnalysisRepositoryError:
        raise ResumeAnalysisServiceError(
            "Unable to save analysis results.",
            status_code=500,
        ) from None

    return _document_to_response(saved, cached=False)
