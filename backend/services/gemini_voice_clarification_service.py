import logging

from google.genai import types
from pydantic import ValidationError

from core.config.settings import settings
from schemas.interview_schema import (
    GeminiVoiceClarificationPayload,
    InterviewerTone,
    InterviewLanguageSettings,
)
from services.interview_language_service import (
    LANGUAGE_LABELS,
    default_language_settings,
)
from services.gemini_client import build_gemini_client, call_with_transient_retries
from services.gemini_config import get_gemini_api_key, get_gemini_model

logger = logging.getLogger(__name__)

TONE_INSTRUCTIONS = {
    "friendly": "Use a warm, encouraging tone.",
    "professional": "Use a neutral, professional interview tone.",
    "challenging": "Use a direct, probing tone without being rude.",
}


class VoiceClarificationError(Exception):
    pass


def _build_prompt(
    *,
    role: str,
    question: str,
    category: str,
    answer_draft: str,
    tone: InterviewerTone,
    prior_transcript: list[dict],
) -> str:
    history_lines = []
    for item in prior_transcript[-6:]:
        history_lines.append(f"[{item.get('role')}]: {item.get('text', '')[:500]}")
    history = "\n".join(history_lines) or "(none)"
    return (
        f"Interview role: {role}\n"
        f"Question category: {category}\n"
        f"Interviewer tone: {tone}\n\n"
        f"CURRENT QUESTION:\n{question}\n\n"
        f"CANDIDATE DRAFT ANSWER:\n{answer_draft}\n\n"
        f"PRIOR TRANSCRIPT (this question only context):\n{history}\n"
    )


def _system_instruction(language: InterviewLanguageSettings) -> str:
    ql = LANGUAGE_LABELS[language.question_language]
    return f"""You are a voice interviewer reviewing a draft answer.

Rules:
- interviewer_message must be in {ql} when needs_clarification is true (unless question is English-only practice).
- Decide if a brief clarification or follow-up is needed before scoring.
- needs_clarification=true only when the draft is too vague, off-topic, or missing a critical part.
- Do not repeat the full question verbatim.
- Do not provide the ideal answer or scoring.
- interviewer_message must be one short spoken-style prompt (under 400 chars) or null.
- Never invent candidate experience.
- Keep technical terms accurate; do not mistranslate jargon.
"""


def evaluate_voice_clarification(
    *,
    role: str,
    question: str,
    category: str,
    answer_draft: str,
    tone: InterviewerTone,
    prior_transcript: list[dict],
    language_settings: InterviewLanguageSettings | None = None,
) -> GeminiVoiceClarificationPayload:
    language = language_settings or default_language_settings()
    if not answer_draft.strip():
        return GeminiVoiceClarificationPayload(
            needs_clarification=True,
            interviewer_message="Could you share more detail in your own words?",
        )

    api_key = get_gemini_api_key()
    model = get_gemini_model()
    client = build_gemini_client(api_key)
    tone_line = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["professional"])

    def _call():
        return client.models.generate_content(
            model=model,
            contents=_build_prompt(
                role=role,
                question=question,
                category=category,
                answer_draft=answer_draft.strip()[: settings.INTERVIEW_MAX_ANSWER_CHARS],
                tone=tone,
                prior_transcript=prior_transcript,
            ),
            config=types.GenerateContentConfig(
                system_instruction=f"{_system_instruction(language)}\n{tone_line}",
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=GeminiVoiceClarificationPayload,
            ),
        )

    try:
        response = call_with_transient_retries(
            _call,
            max_attempts=max(int(settings.GEMINI_APP_RETRY_ATTEMPTS), 1),
            initial_delay=float(settings.GEMINI_RETRY_INITIAL_DELAY_SECONDS),
            max_delay=float(settings.GEMINI_RETRY_MAX_DELAY_SECONDS),
            operation_name="gemini_voice_clarification",
        )
    except Exception as exc:
        logger.warning("Voice clarification failed: %s", type(exc).__name__)
        raise VoiceClarificationError("Clarification check unavailable.") from exc

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise VoiceClarificationError("Empty clarification response.")

    try:
        return GeminiVoiceClarificationPayload.model_validate_json(raw_text)
    except ValidationError as exc:
        raise VoiceClarificationError("Invalid clarification structure.") from exc
