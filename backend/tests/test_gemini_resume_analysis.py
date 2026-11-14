import json
from unittest.mock import MagicMock, patch

import pytest
from google.genai import errors as genai_errors

from services.gemini_client import (
    call_with_transient_retries,
    is_non_retryable_gemini_error,
    is_transient_gemini_error,
    sanitize_provider_error,
)
from services.gemini_resume_analysis_service import (
    GeminiAuthError,
    GeminiRateLimitError,
    GeminiResponseError,
    GeminiUnavailableError,
    _map_genai_exception,
    analyze_resume_text,
)
from tests.fixtures_analysis import sample_gemini_analysis_result


def test_sanitize_provider_error_from_server_error():
    exc = genai_errors.ServerError(
        503,
        {"error": {"code": 503, "status": "UNAVAILABLE", "message": "Overloaded"}},
    )
    info = sanitize_provider_error(exc)
    assert info["exception_type"] == "ServerError"
    assert info["http_status"] == 503
    assert info["provider_status"] == "UNAVAILABLE"


def test_map_server_error_503_to_unavailable():
    exc = genai_errors.ServerError(503, {"error": {"message": "unavailable"}})
    mapped = _map_genai_exception(exc)
    assert isinstance(mapped, GeminiUnavailableError)


def test_map_client_error_401_to_auth():
    exc = genai_errors.ClientError(401, {"error": {"message": "API key not valid"}})
    mapped = _map_genai_exception(exc)
    assert isinstance(mapped, GeminiAuthError)


def test_map_client_error_429_to_rate_limit():
    exc = genai_errors.ClientError(429, {"error": {"message": "Resource exhausted"}})
    mapped = _map_genai_exception(exc)
    assert isinstance(mapped, GeminiRateLimitError)


def test_transient_retry_succeeds_after_503():
    calls = {"count": 0}

    def flaky():
        calls["count"] += 1
        if calls["count"] < 2:
            raise genai_errors.ServerError(503, {"error": {"message": "try again"}})
        return "ok"

    with patch("services.gemini_client.time.sleep"):
        result = call_with_transient_retries(
            flaky,
            max_attempts=3,
            initial_delay=0.1,
            max_delay=1.0,
            operation_name="test",
        )
    assert result == "ok"
    assert calls["count"] == 2


def test_transient_retry_exhausted_raises():
    def always_fail():
        raise genai_errors.ServerError(503, {"error": {"message": "down"}})

    with patch("services.gemini_client.time.sleep"):
        with pytest.raises(genai_errors.ServerError):
            call_with_transient_retries(
                always_fail,
                max_attempts=2,
                initial_delay=0.1,
                max_delay=1.0,
                operation_name="test",
            )


def test_non_retryable_auth_not_retried():
    calls = {"count": 0}

    def auth_fail():
        calls["count"] += 1
        raise genai_errors.ClientError(401, {"error": {"message": "invalid key"}})

    with patch("services.gemini_client.time.sleep"):
        with pytest.raises(genai_errors.ClientError):
            call_with_transient_retries(
                auth_fail,
                max_attempts=3,
                initial_delay=0.1,
                max_delay=1.0,
                operation_name="test",
            )
    assert calls["count"] == 1
    assert is_non_retryable_gemini_error(
        genai_errors.ClientError(401, {"error": {"message": "x"}})
    )


def test_timeout_is_transient():
    assert is_transient_gemini_error(TimeoutError())


@patch("services.gemini_resume_analysis_service._generate_analysis")
def test_analyze_resume_text_success(mock_generate):
    payload = sample_gemini_analysis_result()
    mock_response = MagicMock()
    mock_response.text = json.dumps({"analysis": payload.analysis.model_dump()})
    mock_generate.return_value = mock_response

    result = analyze_resume_text("Python engineer resume text long enough here.")
    assert result.analysis.professional_summary


@patch("services.gemini_resume_analysis_service._generate_analysis")
def test_analyze_resume_text_invalid_json(mock_generate):
    mock_response = MagicMock()
    mock_response.text = '{"analysis": {"professional_summary": "x"}}'
    mock_generate.return_value = mock_response

    with pytest.raises(GeminiResponseError):
        analyze_resume_text("Python engineer resume text long enough here.")
