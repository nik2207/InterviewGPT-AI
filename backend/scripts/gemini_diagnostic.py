"""Sanitized Gemini connectivity diagnostic (no secrets in output).

Usage (from backend/):
  .\\venv\\Scripts\\python.exe scripts/gemini_diagnostic.py
  .\\venv\\Scripts\\python.exe scripts/gemini_diagnostic.py --structured
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from core.config.settings import settings
from schemas.analysis_schema import GeminiResumeAnalysisResult
from services.gemini_config import get_gemini_api_key, get_gemini_model
from services.gemini_client import build_gemini_client
from services.gemini_client import sanitize_provider_error
from services.gemini_resume_analysis_service import SYSTEM_INSTRUCTION, _build_prompt


SYNTHETIC_RESUME = """
Jane Candidate
Software Engineer

Skills: Python, FastAPI, MongoDB, REST APIs.

Experience:
- Backend Developer at Example Corp (2022–present): Built API services and tests.

Projects:
- Inventory API: FastAPI service with JWT authentication.
""".strip()


def _report_exception(exc: BaseException) -> None:
    info = sanitize_provider_error(exc)
    print(f"exception_type={info['exception_type']}")
    print(f"http_status={info.get('http_status')}")
    print(f"provider_status={info.get('provider_status')}")
    print(f"provider_message={info.get('provider_message')}")


def _minimal_ping(client: genai.Client, model: str) -> bool:
    print(f"model={model}")
    print("step=minimal_generate_content")
    try:
        response = client.models.generate_content(
            model=model,
            contents="Reply with exactly: ok",
            config=types.GenerateContentConfig(temperature=0),
        )
        text = (getattr(response, "text", None) or "").strip()
        print(f"minimal_success=True")
        print(f"response_length={len(text)}")
        return True
    except Exception as exc:
        print("minimal_success=False")
        _report_exception(exc)
        return False


def _structured_probe(client: genai.Client, model: str) -> bool:
    print("step=structured_resume_analysis")
    try:
        response = client.models.generate_content(
            model=model,
            contents=_build_prompt(SYNTHETIC_RESUME),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=GeminiResumeAnalysisResult,
            ),
        )
        raw = getattr(response, "text", None) or ""
        print(f"structured_success=True")
        print(f"response_length={len(raw)}")
        return True
    except Exception as exc:
        print("structured_success=False")
        _report_exception(exc)
        return False


def _list_models(client: genai.Client) -> None:
    print("step=list_models")
    try:
        models = list(client.models.list())
        names = sorted({m.name for m in models if getattr(m, "name", None)})[:25]
        print(f"models_listed={len(models)}")
        for name in names:
            print(f"  model_name={name}")
        if len(models) > len(names):
            print(f"  (showing first {len(names)} names only)")
    except Exception as exc:
        print("list_models_success=False")
        _report_exception(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Gemini API diagnostic")
    parser.add_argument(
        "--structured",
        action="store_true",
        help="Also run structured-output resume analysis probe",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List models visible to the configured API key",
    )
    args = parser.parse_args()

    try:
        api_key = get_gemini_api_key()
        model = get_gemini_model()
    except Exception as exc:
        print(f"config_error={type(exc).__name__}: {exc}")
        return 1

    print(f"api_key_configured=True (length={len(api_key)})")
    client = build_gemini_client(api_key)

    ok = _minimal_ping(client, model)
    if args.structured and ok:
        _structured_probe(client, model)
    elif args.structured and not ok:
        print("structured_skipped=True (minimal call failed)")

    if args.list_models:
        _list_models(client)

    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
