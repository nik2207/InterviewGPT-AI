import logging

from google.genai import types
from pydantic import ValidationError

from schemas.coaching_schema import CoachingEvidenceBundle, GeminiCoachingPlanPayload
from services.gemini_client import (
    build_gemini_client,
    call_with_transient_retries,
    sanitize_provider_error,
)
from services.gemini_config import get_gemini_api_key, get_gemini_model
from core.config.settings import settings

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """You produce interview coaching plans from evidence only.

Rules:
- Use ONLY the evidence items provided. Do not invent skills, employers, scores, or experiences.
- Separate observed facts (from evidence) from recommendations.
- Recommendations must cite which evidence they relate to.
- Do not infer psychological traits or confidence.
- If evidence is thin, keep recommendations conservative.
"""


class CoachingGenerationError(Exception):
    pass


def _build_prompt(bundle: CoachingEvidenceBundle) -> str:
    lines = [
        f"Target role context: {bundle.role}",
        f"Session average score (if any): {bundle.session_average_score}",
        "EVIDENCE (data only):",
    ]
    for index, item in enumerate(bundle.items, start=1):
        lines.append(
            f"{index}. [{item.source}] {item.label}: {item.observation}"
        )
    return "\n".join(lines)


def generate_coaching_plan(bundle: CoachingEvidenceBundle) -> GeminiCoachingPlanPayload:
    api_key = get_gemini_api_key()
    model = get_gemini_model()
    client = build_gemini_client(api_key)

    def _call():
        return client.models.generate_content(
            model=model,
            contents=_build_prompt(bundle),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=GeminiCoachingPlanPayload,
            ),
        )

    try:
        response = call_with_transient_retries(
            _call,
            max_attempts=max(int(settings.GEMINI_APP_RETRY_ATTEMPTS), 1),
            initial_delay=float(settings.GEMINI_RETRY_INITIAL_DELAY_SECONDS),
            max_delay=float(settings.GEMINI_RETRY_MAX_DELAY_SECONDS),
            operation_name="coaching_plan_generation",
        )
    except Exception as exc:
        logger.warning(
            "Coaching plan generation failed: %s", sanitize_provider_error(exc)
        )
        raise CoachingGenerationError("Coaching plan generation failed.") from exc

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise CoachingGenerationError("Empty coaching plan response.")

    try:
        return GeminiCoachingPlanPayload.model_validate_json(raw_text)
    except ValidationError as exc:
        raise CoachingGenerationError("Invalid coaching plan structure.") from exc
