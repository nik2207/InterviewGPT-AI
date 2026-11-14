from typing import Any

from schemas.interview_schema import (
    MULTILINGUAL_PRACTICE_DISCLAIMER,
    InterviewLanguageCode,
    InterviewLanguageSettings,
)

LANGUAGE_LABELS: dict[InterviewLanguageCode, str] = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
}

SPEECH_RECOGNITION_BCP47: dict[InterviewLanguageCode, str] = {
    "en": "en-US",
    "hi": "hi-IN",
    "mr": "mr-IN",
}

# Conservative hints for UI — browsers vary; never guarantee recognition.
SPEECH_RECOGNITION_TYPICAL_SUPPORT: dict[InterviewLanguageCode, str] = {
    "en": "widely_supported",
    "hi": "often_supported",
    "mr": "limited_support",
}


def default_language_settings() -> InterviewLanguageSettings:
    return InterviewLanguageSettings()


def resolve_language_settings(document: dict[str, Any]) -> InterviewLanguageSettings:
    raw = document.get("language_settings")
    if not raw:
        return default_language_settings()
    return InterviewLanguageSettings.model_validate(raw)


def language_settings_to_document(settings: InterviewLanguageSettings) -> dict:
    return settings.model_dump()


def build_evaluation_language_context(settings: InterviewLanguageSettings) -> dict[str, str]:
    return {
        "question_language": LANGUAGE_LABELS[settings.question_language],
        "answer_language": LANGUAGE_LABELS[settings.answer_language],
        "feedback_language": LANGUAGE_LABELS[settings.feedback_language],
        "allow_bilingual": "yes" if settings.allow_bilingual_answers else "no",
        "practice_professional_english": (
            "yes" if settings.practice_professional_english else "no"
        ),
        "disclaimer": MULTILINGUAL_PRACTICE_DISCLAIMER,
    }
