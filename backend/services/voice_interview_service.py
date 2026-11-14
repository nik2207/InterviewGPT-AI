from datetime import datetime, timezone

from repositories.interview_repository import InterviewRepository, InterviewRepositoryError
from schemas.interview_schema import (
    AppendVoiceTranscriptRequest,
    InterviewerTone,
    UpdateVoiceSessionStatusRequest,
    VoiceClarificationRequest,
    VoiceClarificationResponse,
    VoiceInterviewState,
    VoiceTranscriptEntry,
)
from services.gemini_voice_clarification_service import (
    VoiceClarificationError,
    evaluate_voice_clarification,
)
from services.interview_language_service import resolve_language_settings


class VoiceInterviewServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def build_voice_state(enabled: bool, tone: InterviewerTone) -> dict:
    return VoiceInterviewState(
        enabled=enabled,
        tone=tone,
        session_status="active",
        transcript=[],
    ).model_dump(mode="json")


def _get_voice(session: dict) -> dict | None:
    voice = session.get("voice_interview")
    if not voice or not voice.get("enabled"):
        return None
    return voice


async def append_transcript(
    user_id: str,
    session_id: str,
    payload: AppendVoiceTranscriptRequest,
    interview_repo: InterviewRepository,
) -> VoiceInterviewState:
    session = await interview_repo.find_by_id_for_user(session_id, user_id)
    if session is None:
        raise VoiceInterviewServiceError("Interview session not found", status_code=404)
    if _get_voice(session) is None:
        raise VoiceInterviewServiceError(
            "Voice interview is not enabled for this session.",
            status_code=422,
        )

    lang_settings = resolve_language_settings(session)
    entry_lang = (
        lang_settings.question_language
        if payload.role == "interviewer"
        else lang_settings.answer_language
    )
    entry = VoiceTranscriptEntry(
        role=payload.role,
        text=payload.text.strip(),
        question_id=payload.question_id,
        created_at=datetime.now(timezone.utc),
        language=entry_lang,
    ).model_dump(mode="json")

    try:
        updated = await interview_repo.append_voice_transcript(
            session_id, user_id, entry
        )
    except InterviewRepositoryError as exc:
        raise VoiceInterviewServiceError(str(exc), status_code=500) from exc

    if updated is None:
        raise VoiceInterviewServiceError("Unable to append transcript.", status_code=400)

    return VoiceInterviewState.model_validate(updated["voice_interview"])


async def update_voice_status(
    user_id: str,
    session_id: str,
    payload: UpdateVoiceSessionStatusRequest,
    interview_repo: InterviewRepository,
) -> VoiceInterviewState:
    session = await interview_repo.find_by_id_for_user(session_id, user_id)
    if session is None:
        raise VoiceInterviewServiceError("Interview session not found", status_code=404)
    if _get_voice(session) is None:
        raise VoiceInterviewServiceError(
            "Voice interview is not enabled for this session.",
            status_code=422,
        )

    try:
        updated = await interview_repo.update_voice_session_status(
            session_id, user_id, payload.session_status
        )
    except InterviewRepositoryError as exc:
        raise VoiceInterviewServiceError(str(exc), status_code=500) from exc

    if updated is None:
        raise VoiceInterviewServiceError("Unable to update voice status.", status_code=400)

    return VoiceInterviewState.model_validate(updated["voice_interview"])


async def request_clarification(
    user_id: str,
    session_id: str,
    payload: VoiceClarificationRequest,
    interview_repo: InterviewRepository,
) -> VoiceClarificationResponse:
    session = await interview_repo.find_by_id_for_user(session_id, user_id)
    if session is None:
        raise VoiceInterviewServiceError("Interview session not found", status_code=404)

    voice = _get_voice(session)
    if voice is None:
        raise VoiceInterviewServiceError(
            "Voice interview is not enabled for this session.",
            status_code=422,
        )

    question = next(
        (q for q in session.get("questions", []) if q.get("id") == payload.question_id),
        None,
    )
    if question is None:
        raise VoiceInterviewServiceError("Question not found in session.", status_code=404)

    prior = [
        item
        for item in voice.get("transcript", [])
        if item.get("question_id") in (None, payload.question_id)
    ]

    try:
        lang_settings = resolve_language_settings(session)
        result = evaluate_voice_clarification(
            role=session.get("role", "Interview"),
            question=question.get("question", ""),
            category=question.get("category", "general"),
            answer_draft=payload.answer_draft,
            tone=voice.get("tone", "professional"),
            prior_transcript=prior,
            language_settings=lang_settings,
        )
    except VoiceClarificationError as exc:
        raise VoiceInterviewServiceError(str(exc), status_code=503) from exc

    if result.needs_clarification and result.interviewer_message:
        entry = VoiceTranscriptEntry(
            role="interviewer",
            text=result.interviewer_message.strip(),
            question_id=payload.question_id,
            created_at=datetime.now(timezone.utc),
            language=lang_settings.question_language,
        ).model_dump(mode="json")
        await interview_repo.append_voice_transcript(session_id, user_id, entry)

    return VoiceClarificationResponse(
        needs_clarification=result.needs_clarification,
        interviewer_message=result.interviewer_message,
    )
