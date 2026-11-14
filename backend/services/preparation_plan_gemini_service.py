import logging

from google.genai import types
from pydantic import ValidationError

from core.config.settings import settings
from schemas.preparation_plan_schema import (
    DAY_THEMES,
    GeminiSevenDayPlanPayload,
    PreparationPlanEvidenceBundle,
)
from services.gemini_client import build_gemini_client, call_with_transient_retries
from services.gemini_config import get_gemini_api_key, get_gemini_model

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """You create a personalised 7-day interview preparation plan.

Rules:
- Use ONLY evidence provided. Do not invent employers, projects, degrees, or scores.
- Each day_number 1-7 must follow the fixed theme for that day (provided in the prompt).
- Content must be specific to the candidate's gaps and target role — not generic boilerplate.
- Scale estimated_duration_minutes near the user's daily study budget.
- interview_questions must be answerable in writing/voice practice.
- practical_exercise may be null only when not appropriate that day.
- Never assign psychological traits or guaranteed outcomes.
"""


class PreparationPlanGenerationError(Exception):
    pass


def _build_prompt(bundle: PreparationPlanEvidenceBundle) -> str:
    theme_lines = [f"Day {n}: {theme}" for n, theme in DAY_THEMES.items()]
    lines = [
        f"Target role: {bundle.target_role}",
        f"Daily study budget (minutes): {bundle.daily_study_minutes}",
        f"Average interview score (if any): {bundle.average_interview_score}",
        f"Technical weaknesses: {', '.join(bundle.weakness_technical) or 'none listed'}",
        f"Behavioural weaknesses: {', '.join(bundle.weakness_behavioral) or 'none listed'}",
        "",
        "FIXED DAY THEMES (personalise activities within each theme):",
        *theme_lines,
        "",
        "EVIDENCE (data only):",
    ]
    for index, item in enumerate(bundle.items, start=1):
        lines.append(f"{index}. [{item.source}] {item.label}: {item.observation}")
    return "\n".join(lines)


def generate_seven_day_plan(
    bundle: PreparationPlanEvidenceBundle,
) -> GeminiSevenDayPlanPayload:
    api_key = get_gemini_api_key()
    model = get_gemini_model()
    client = build_gemini_client(api_key)

    def _call():
        return client.models.generate_content(
            model=model,
            contents=_build_prompt(bundle),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.25,
                response_mime_type="application/json",
                response_schema=GeminiSevenDayPlanPayload,
            ),
        )

    try:
        response = call_with_transient_retries(
            _call,
            max_attempts=max(int(settings.GEMINI_APP_RETRY_ATTEMPTS), 1),
            initial_delay=float(settings.GEMINI_RETRY_INITIAL_DELAY_SECONDS),
            max_delay=float(settings.GEMINI_RETRY_MAX_DELAY_SECONDS),
            operation_name="preparation_plan_generation",
        )
    except Exception as exc:
        logger.warning("Preparation plan generation failed: %s", type(exc).__name__)
        raise PreparationPlanGenerationError("Plan generation failed.") from exc

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise PreparationPlanGenerationError("Empty preparation plan response.")

    try:
        payload = GeminiSevenDayPlanPayload.model_validate_json(raw_text)
    except ValidationError as exc:
        raise PreparationPlanGenerationError("Invalid preparation plan structure.") from exc

    for day in payload.days:
        if day.day_number not in DAY_THEMES:
            raise PreparationPlanGenerationError("Invalid day numbering in plan.")

    return payload
