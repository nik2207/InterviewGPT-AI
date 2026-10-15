from core.config.settings import settings


class GeminiConfigurationError(Exception):
    """Raised when Gemini is not configured for analysis."""


def get_gemini_api_key() -> str:
    key = (settings.GEMINI_API_KEY or "").strip()
    placeholders = {"", "your_gemini_api_key", "changeme", "placeholder"}
    if key.lower() in placeholders:
        raise GeminiConfigurationError(
            "GEMINI_API_KEY is not configured. Set it in backend/.env."
        )
    return key


def get_gemini_model() -> str:
    model = (settings.GEMINI_MODEL or "").strip()
    if not model:
        raise GeminiConfigurationError(
            "GEMINI_MODEL is not configured. Set it in backend/.env."
        )
    return model
