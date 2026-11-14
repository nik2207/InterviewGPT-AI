import logging

from google.genai import types
from pydantic import ValidationError

from core.config.settings import settings
from schemas.interview_schema import (
    GeminiFollowUpQuestionPayload,
    InterviewLanguageSettings,
)
from services.interview_language_service import (
    LANGUAGE_LABELS,
    default_language_settings,
)
from services.gemini_client import build_gemini_client, call_with_transient_retries
from services.gemini_config import get_gemini_api_key, get_gemini_model

logger = logging.getLogger(__name__)

def _system_instruction(language: InterviewLanguageSettings) -> str:
    label = LANGUAGE_LABELS[language.question_language]
    lang_rule = (
        f"Write the follow-up question in {label} when should_ask_follow_up is true."
        if language.question_language != "en"
        else "Write the follow-up question in English."
    )
    return f"""You decide whether one interview follow-up question is needed.

Rules:
- {lang_rule}
- Preserve technical terms in English when natural.
- should_ask_follow_up=true only when clarification, depth, example, scenario, project detail,
  or behavioural exploration would add value based on the answer.
- Do not repeat the original question wording.
- Do not ask unrelated questions.
- Never provide model answers or scoring.
- If the answer is strong and complete, should_ask_follow_up=false.
- follow_up_type must be one of: clarification, technical_depth, practical_scenario,
  project_explanation, behavioural_exploration.
- When should_ask_follow_up is false, leave question null.
"""


SYSTEM_INSTRUCTION = _system_instruction(default_language_settings())


class FollowUpGenerationError(Exception):
    pass


def _build_prompt(
    *,
    role: str,
    interview_type: str,
    parent_question: dict,
    answer_text: str,
    evaluation: dict,
    existing_questions: list[str],
) -> str:
    dims = evaluation.get("dimension_scores") or {}
    missing = evaluation.get("missing_concepts") or []
    coach = evaluation.get("improvement_coach") or {}
    coach_gaps = coach.get("missing_important_points") or []

    existing = "\n".join(f"- {q[:200]}" for q in existing_questions[:12])

    return (
        f"Role: {role}\n"
        f"Interview type: {interview_type}\n"
        f"PARENT QUESTION:\n{parent_question.get('question', '')}\n"
        f"Category: {parent_question.get('category')}\n\n"
        f"ANSWER:\n{answer_text[:3000]}\n\n"
        f"Dimension scores: {dims}\n"
        f"Missing concepts: {missing}\n"
        f"Coach gaps: {coach_gaps}\n\n"
        f"EXISTING QUESTIONS (do not duplicate):\n{existing}\n"
    )


def generate_follow_up_question(
    *,
    role: str,
    interview_type: str,
    parent_question: dict,
    answer_text: str,
    evaluation: dict,
    existing_questions: list[str],
    language_settings: InterviewLanguageSettings | None = None,
) -> GeminiFollowUpQuestionPayload:
    language = language_settings or default_language_settings()
    api_key = get_gemini_api_key()
    model = get_gemini_model()
    client = build_gemini_client(api_key)

    def _call():
        return client.models.generate_content(
            model=model,
            contents=_build_prompt(
                role=role,
                interview_type=interview_type,
                parent_question=parent_question,
                answer_text=answer_text,
                evaluation=evaluation,
                existing_questions=existing_questions,
            ),
            config=types.GenerateContentConfig(
                system_instruction=_system_instruction(language),
                temperature=0.25,
                response_mime_type="application/json",
                response_schema=GeminiFollowUpQuestionPayload,
            ),
        )

    try:
        response = call_with_transient_retries(
            _call,
            max_attempts=max(int(settings.GEMINI_APP_RETRY_ATTEMPTS), 1),
            initial_delay=float(settings.GEMINI_RETRY_INITIAL_DELAY_SECONDS),
            max_delay=float(settings.GEMINI_RETRY_MAX_DELAY_SECONDS),
            operation_name="gemini_follow_up_question",
        )
    except Exception as exc:
        logger.warning("Follow-up generation failed: %s", type(exc).__name__)
        raise FollowUpGenerationError("Follow-up generation failed.") from exc

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise FollowUpGenerationError("Empty follow-up response.")

    try:
        return GeminiFollowUpQuestionPayload.model_validate_json(raw_text)
    except ValidationError as exc:
        raise FollowUpGenerationError("Invalid follow-up structure.") from exc
