import logging
from typing import Any

from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from core.config.settings import settings
from schemas.resume_builder_schema import RESUME_AI_DISCLAIMER, ResumeAiFeature
from services.gemini_client import build_gemini_client, call_with_transient_retries
from services.gemini_config import get_gemini_api_key, get_gemini_model

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """You assist with ATS-friendly resume WRITING using only user-provided facts.

Rules:
- NEVER invent employers, job titles, dates, schools, certifications, awards, metrics, or project outcomes.
- ONLY rephrase, reorganise, or highlight information explicitly present in the input.
- For missing_info: list gaps in user-provided content without fabricating filler.
- For job_keywords: suggest keywords from the job description that align with existing resume content; flag when resume lacks evidence.
- For ats_formatting: describe formatting readability issues (dense text, special characters, missing sections) — no guaranteed score.
- Use strong action verbs when rewriting bullets without changing factual meaning.
- improved_text must not add facts absent from original_text/context.
"""


class GeminiResumeAiPayload(BaseModel):
    original_text: str = Field(..., max_length=12000)
    improved_text: str = Field(..., max_length=12000)
    comparison_notes: str = Field(..., max_length=2500)
    missing_information: list[str] = Field(default_factory=list, max_length=15)
    keyword_suggestions: list[str] = Field(default_factory=list, max_length=30)
    ats_formatting_notes: list[str] = Field(default_factory=list, max_length=15)


class ResumeBuilderAiError(Exception):
    pass


class ResumeBuilderAiUnavailableError(ResumeBuilderAiError):
    pass


def _build_prompt(feature: ResumeAiFeature, context: str, extra: str = "") -> str:
    return (
        f"Feature: {feature}\n"
        f"Context:\n{context[:10000]}\n"
        f"{extra[:5000]}"
    )


def run_resume_builder_ai(
    *,
    feature: ResumeAiFeature,
    context: str,
    extra: str = "",
) -> GeminiResumeAiPayload:
    api_key = get_gemini_api_key()
    model = get_gemini_model()
    client = build_gemini_client(api_key)

    def _call():
        return client.models.generate_content(
            model=model,
            contents=_build_prompt(feature, context, extra),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.25,
                response_mime_type="application/json",
                response_schema=GeminiResumeAiPayload,
            ),
        )

    try:
        response = call_with_transient_retries(
            _call,
            max_attempts=max(int(settings.GEMINI_APP_RETRY_ATTEMPTS), 1),
            initial_delay=float(settings.GEMINI_RETRY_INITIAL_DELAY_SECONDS),
            max_delay=float(settings.GEMINI_RETRY_MAX_DELAY_SECONDS),
            operation_name=f"resume_builder_ai_{feature}",
        )
    except Exception as exc:
        logger.warning("Resume builder AI failed: %s", type(exc).__name__)
        raise ResumeBuilderAiUnavailableError("AI assistance unavailable.") from exc

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise ResumeBuilderAiError("Empty AI response.")

    try:
        return GeminiResumeAiPayload.model_validate_json(raw_text)
    except ValidationError as exc:
        raise ResumeBuilderAiError("Invalid AI response.") from exc


def payload_to_proposal(feature: ResumeAiFeature, payload: GeminiResumeAiPayload) -> dict[str, Any]:
    return {
        "feature": feature,
        "original_text": payload.original_text,
        "improved_text": payload.improved_text,
        "comparison_notes": payload.comparison_notes,
        "missing_information": payload.missing_information,
        "keyword_suggestions": payload.keyword_suggestions,
        "ats_formatting_notes": payload.ats_formatting_notes,
        "requires_user_confirmation": True,
        "disclaimer": RESUME_AI_DISCLAIMER,
    }
