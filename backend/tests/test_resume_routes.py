from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from core.dependencies import (
    get_resume_repository,
    get_session_repository,
    get_user_repository,
)
from tests.test_auth_routes import InMemorySessionRepository
from core.security.jwt import create_access_token
from services.pdf_extractor import PdfExtractionError
from tests.pdf_fixtures import build_text_pdf


@pytest.fixture
def resume_client(client: TestClient, sample_user_document: dict):
    resume_repo = AsyncMock()
    resume_repo.create_resume = AsyncMock(
        return_value={
            "_id": ObjectId("507f1f77bcf86cd799439012"),
            "user_id": str(sample_user_document["_id"]),
            "original_filename": "resume.pdf",
            "file_size_bytes": 1024,
            "uploaded_at": datetime.now(timezone.utc),
            "extracted_text": "hidden",
            "page_count": 1,
            "parsing_status": "parsed",
            "content_sha256": "sha",
        }
    )
    resume_repo.list_by_user = AsyncMock(return_value=[])

    user_repo = AsyncMock()
    user_repo.find_by_id = AsyncMock(return_value=sample_user_document)

    from app.main import app

    session_repo = InMemorySessionRepository()

    app.dependency_overrides[get_resume_repository] = lambda: resume_repo
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo

    token, _, _ = create_access_token(
        str(sample_user_document["_id"]),
        sample_user_document["email"],
    )

    yield client, resume_repo, {"Authorization": f"Bearer {token}"}

    app.dependency_overrides.clear()


def test_upload_requires_authentication(client: TestClient):
    pdf = build_text_pdf(
        "Authenticated upload tests need enough extractable resume text content."
    )
    response = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.pdf", BytesIO(pdf), "application/pdf")},
    )
    assert response.status_code == 401


def test_upload_valid_pdf(resume_client):
    client, resume_repo, headers = resume_client
    pdf = build_text_pdf(
        "Professional summary with enough extractable resume text for upload."
    )

    response = client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("resume.pdf", BytesIO(pdf), "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["resume"]["original_filename"] == "resume.pdf"
    assert "extracted_text" not in body
    assert "extracted_text" not in body["resume"]
    resume_repo.create_resume.assert_awaited_once()


def test_upload_rejects_non_pdf(resume_client):
    client, _, headers = resume_client
    response = client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("resume.pdf", BytesIO(b"not-a-pdf"), "application/pdf")},
    )
    assert response.status_code == 422
    assert "valid PDF" in response.json()["detail"]


def test_upload_rejects_empty_file(resume_client):
    client, _, headers = resume_client
    response = client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("resume.pdf", BytesIO(b""), "application/pdf")},
    )
    assert response.status_code == 400


def test_upload_rejects_oversized_file(resume_client, monkeypatch):
    client, _, headers = resume_client
    monkeypatch.setattr(
        "services.resume_upload_service.settings.RESUME_MAX_FILE_BYTES",
        128,
    )
    pdf = build_text_pdf(
        "This resume content should exceed the configured upload size limit."
    )
    response = client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("resume.pdf", BytesIO(pdf), "application/pdf")},
    )
    assert response.status_code == 413


def test_list_resumes_returns_metadata_only(resume_client, sample_user_document):
    client, resume_repo, headers = resume_client
    resume_repo.list_by_user = AsyncMock(
        return_value=[
            {
                "_id": ObjectId("507f1f77bcf86cd799439012"),
                "user_id": str(sample_user_document["_id"]),
                "original_filename": "resume.pdf",
                "file_size_bytes": 1024,
                "uploaded_at": datetime.now(timezone.utc),
                "extracted_text": "hidden",
                "page_count": 2,
                "parsing_status": "parsed",
                "content_sha256": "sha",
            }
        ]
    )

    response = client.get("/api/v1/resumes", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["resumes"]) == 1
    assert body["resumes"][0]["page_count"] == 2
    assert "extracted_text" not in body["resumes"][0]


def test_upload_parser_error_returns_safe_message(resume_client, monkeypatch):
    client, resume_repo, headers = resume_client

    def _raise_scanned_error(_content: bytes):
        raise PdfExtractionError(
            "This PDF does not contain enough extractable text. "
            "Scanned/image-only resumes are not supported in this phase."
        )

    monkeypatch.setattr(
        "services.resume_upload_service.extract_text_from_pdf",
        _raise_scanned_error,
    )

    pdf = build_text_pdf("Enough text here for upload request validation path.")
    response = client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("resume.pdf", BytesIO(pdf), "application/pdf")},
    )
    assert response.status_code == 422
    assert "OCR" in response.json()["detail"] or "Scanned" in response.json()["detail"]
    resume_repo.create_resume.assert_not_called()
