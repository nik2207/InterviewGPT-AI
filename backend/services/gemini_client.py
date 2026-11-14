import logging
import random
import time
from typing import Any, Callable, TypeVar

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from core.config.settings import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

_TRANSIENT_HTTP_CODES = frozenset({408, 429, 500, 502, 503, 504})


def build_gemini_client(api_key: str) -> genai.Client:
    timeout_ms = max(int(settings.GEMINI_REQUEST_TIMEOUT_SECONDS) * 1000, 1000)
    sdk_attempts = max(int(settings.GEMINI_SDK_HTTP_ATTEMPTS), 1)
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=timeout_ms,
            retry_options=types.HttpRetryOptions(
                attempts=sdk_attempts,
                initial_delay=1.0,
                max_delay=min(60.0, float(settings.GEMINI_RETRY_MAX_DELAY_SECONDS)),
                exp_base=2.0,
                jitter=1.0,
                http_status_codes=sorted(_TRANSIENT_HTTP_CODES),
            ),
        ),
    )


def sanitize_provider_error(exc: BaseException) -> dict[str, Any]:
    info: dict[str, Any] = {"exception_type": type(exc).__name__}

    if isinstance(exc, genai_errors.APIError):
        info["http_status"] = getattr(exc, "code", None)
        info["provider_status"] = getattr(exc, "status", None)
        message = getattr(exc, "message", None) or str(exc)
        if message:
            info["provider_message"] = _truncate_safe_message(str(message))

    if isinstance(exc, TimeoutError):
        info["provider_message"] = "Request timed out."

    return info


def _truncate_safe_message(message: str, limit: int = 240) -> str:
    cleaned = " ".join(message.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def is_transient_gemini_error(exc: BaseException) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    if isinstance(exc, genai_errors.ServerError):
        code = getattr(exc, "code", None)
        return code in _TRANSIENT_HTTP_CODES or code is None
    if isinstance(exc, genai_errors.ClientError):
        code = getattr(exc, "code", None)
        return code in (408, 429)
    return False


def is_non_retryable_gemini_error(exc: BaseException) -> bool:
    if isinstance(exc, genai_errors.ClientError):
        code = getattr(exc, "code", None)
        if code in (400, 401, 403, 404):
            return True
        message = str(exc).lower()
        if "api key" in message or "permission" in message:
            return True
        if code == 404 or ("not found" in message and "model" in message):
            return True
    return False


def call_with_transient_retries(
    operation: Callable[[], T],
    *,
    max_attempts: int,
    initial_delay: float,
    max_delay: float,
    operation_name: str,
) -> T:
    attempts = max(max_attempts, 1)
    delay = max(initial_delay, 0.0)
    last_exc: BaseException | None = None

    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as exc:
            last_exc = exc
            if is_non_retryable_gemini_error(exc):
                raise
            if not is_transient_gemini_error(exc) or attempt >= attempts:
                raise
            info = sanitize_provider_error(exc)
            logger.warning(
                "%s transient failure attempt=%s/%s %s",
                operation_name,
                attempt,
                attempts,
                info,
            )
            jitter = random.uniform(0, delay * 0.25)
            time.sleep(min(delay + jitter, max_delay))
            delay = min(delay * 2, max_delay)

    assert last_exc is not None
    raise last_exc
