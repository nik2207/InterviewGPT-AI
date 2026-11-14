import json
import logging

from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from core.config.settings import settings
from schemas.interview_schema import InterviewLanguageCode
from services.gemini_client import build_gemini_client, call_with_transient_retries
from services.gemini_config import get_gemini_api_key, get_gemini_model
from services.interview_language_service import LANGUAGE_LABELS

logger = logging.getLogger(__name__)


class _LocalizationItem(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    question: str = Field(..., min_length=5, max_length=500)


class _LocalizationPayload(BaseModel):
    questions: list[_LocalizationItem] = Field(..., min_length=1, max_length=20)


class QuestionLocalizationError(Exception):
    pass


def _system_instruction(target: InterviewLanguageCode) -> str:
    label = LANGUAGE_LABELS[target]
    return f"""You localize interview practice questions into {label}.

Rules:
- Output JSON only matching the schema.
- Translate natural language; keep widely used technical terms in English when appropriate
  (e.g. API, REST, Kubernetes, Python, SQL, React, microservices).
- Do not change question meaning or difficulty.
- Preserve each id exactly.
- Use professional interview tone suitable for {label}.
"""


def localize_interview_questions(
    questions: list[dict],
    target_language: InterviewLanguageCode,
) -> list[dict]:
    if target_language == "en" or not questions:
        return questions

    items = [
        {"id": q["id"], "question": q["question"][:500]}
        for q in questions
        if q.get("id") and q.get("question")
    ]
    if not items:
        return questions

    api_key = get_gemini_api_key()
    model = get_gemini_model()
    client = build_gemini_client(api_key)
    label = LANGUAGE_LABELS[target_language]

    prompt = (
        f"Target language: {label} ({target_language})\n\n"
        f"Questions JSON:\n{json.dumps(items, ensure_ascii=False)}\n"
    )

    def _call():
        return client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_system_instruction(target_language),
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=_LocalizationPayload,
            ),
        )

    try:
        response = call_with_transient_retries(
            _call,
            max_attempts=max(int(settings.GEMINI_APP_RETRY_ATTEMPTS), 1),
            initial_delay=float(settings.GEMINI_RETRY_INITIAL_DELAY_SECONDS),
            max_delay=float(settings.GEMINI_RETRY_MAX_DELAY_SECONDS),
            operation_name="gemini_interview_localization",
        )
    except Exception as exc:
        logger.warning("Question localization failed: %s", exc)
        raise QuestionLocalizationError("Localization unavailable") from exc

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise QuestionLocalizationError("Empty localization response")

    try:
        payload = _LocalizationPayload.model_validate_json(raw_text)
    except ValidationError as exc:
        raise QuestionLocalizationError("Invalid localization response") from exc

    by_id = {entry.id: entry.question for entry in payload.questions}
    localized = []
    for q in questions:
        copy = dict(q)
        if q.get("id") in by_id:
            copy["question"] = by_id[q["id"]]
        localized.append(copy)
    return localized
