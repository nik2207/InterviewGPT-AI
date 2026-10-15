from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from core.dependencies import (
    get_analysis_repository,
    get_resume_repository,
    get_session_repository,
    get_user_repository,
)
from core.security.jwt import create_access_token
from schemas.analysis_schema import GeminiResumeAnalysisResult
from services.gemini_config import GeminiConfigurationError
from services.gemini_resume_analysis_service import GeminiResponseError
from tests.fixtures_analysis import sample_gemini_analysis_result
from tests.pdf_fixtures import build_text_pdf
from tests.test_auth_routes import InMemorySessionRepository


@pytest.fixture
def analysis_client(client: TestClient, sample_user_document: dict):
    resume_id = ObjectId("507f1f77bcf86cd799439012")
    resume_doc = {
        "_id": resume_id,
        "user_id": str(sample_user_document["_id"]),
        "original_filename": "resume.pdf",
        "file_size_bytes": 1200,
        "uploaded_at": datetime.now(timezone.utc),
        "extracted_text": "Experienced engineer with Python, FastAPI, and MongoDB project delivery.",
        "page_count": 1,
        "parsing_status": "parsed",
        "content_sha256": "sha-resume-1",
    }

    resume_repo = AsyncMock()
    resume_repo.find_by_id_for_user = AsyncMock(return_value=resume_doc)
    resume_repo.list_by_user = AsyncMock(return_value=[resume_doc])

    analysis_repo = AsyncMock()
    analysis_repo.find_latest_matching_content = AsyncMock(return_value=None)
    analysis_repo.find_latest_for_resume = AsyncMock(return_value=None)
    analysis_repo.create_analysis = AsyncMock(
        return_value={
            "_id": ObjectId("507f1f77bcf86cd799439013"),
            "user_id": str(sample_user_document["_id"]),
            "resume_id": str(resume_id),
            "content_sha256": "sha-resume-1",
            "model": "gemini-2.0-flash",
            "status": "completed",
            "analysis": sample_gemini_analysis_result().analysis.model_dump(
                exclude={"interview_questions"}
            ),
            "interview_questions": [
                q.model_dump()
                for q in sample_gemini_analysis_result().analysis.interview_questions
            ],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    )

    user_repo = AsyncMock()
    user_repo.find_by_id = AsyncMock(return_value=sample_user_document)

    from app.main import app

    session_repo = InMemorySessionRepository()
    app.dependency_overrides[get_resume_repository] = lambda: resume_repo
    app.dependency_overrides[get_analysis_repository] = lambda: analysis_repo
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo

    token, _, _ = create_access_token(
        str(sample_user_document["_id"]),
        sample_user_document["email"],
    )

    yield client, resume_repo, analysis_repo, {
        "Authorization": f"Bearer {token}"
    }, str(resume_id)

    app.dependency_overrides.clear()


def test_analyze_requires_auth(client: TestClient):
    response = client.post("/api/v1/resumes/507f1f77bcf86cd799439012/analyze")
    assert response.status_code == 401


def test_analyze_resume_not_found(analysis_client):
    client, resume_repo, _, headers, resume_id = analysis_client
    resume_repo.find_by_id_for_user = AsyncMock(return_value=None)
    response = client.post(
        f"/api/v1/resumes/{resume_id}/analyze",
        headers=headers,
    )
    assert response.status_code == 404


@patch("services.resume_analysis_service.analyze_resume_text")
def test_analyze_success(mock_analyze, analysis_client):
    client, _, analysis_repo, headers, resume_id = analysis_client
    mock_analyze.return_value = sample_gemini_analysis_result()

    response = client.post(
        f"/api/v1/resumes/{resume_id}/analyze",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["resume_id"] == resume_id
    assert len(body["interview_questions"]) >= 8
    assert body["analysis"]["professional_summary"]
    analysis_repo.create_analysis.assert_awaited_once()


@patch("services.resume_analysis_service.analyze_resume_text")
def test_analyze_uses_cache_without_refresh(mock_analyze, analysis_client):
    client, _, analysis_repo, headers, resume_id = analysis_client
    cached_doc = {
        "_id": ObjectId("507f1f77bcf86cd799439099"),
        "user_id": "user",
        "resume_id": resume_id,
        "content_sha256": "sha-resume-1",
        "model": "gemini-2.0-flash",
        "status": "completed",
        "analysis": sample_gemini_analysis_result().analysis.model_dump(
            exclude={"interview_questions"}
        ),
        "interview_questions": [],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    analysis_repo.find_latest_matching_content = AsyncMock(return_value=cached_doc)

    response = client.post(
        f"/api/v1/resumes/{resume_id}/analyze",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["cached"] is True
    mock_analyze.assert_not_called()


@patch("services.resume_analysis_service.analyze_resume_text")
def test_analyze_refresh_bypasses_cache(mock_analyze, analysis_client):
    client, _, analysis_repo, headers, resume_id = analysis_client
    mock_analyze.return_value = sample_gemini_analysis_result()
    analysis_repo.find_latest_matching_content = AsyncMock(
        return_value={"_id": ObjectId(), "status": "completed"}
    )

    response = client.post(
        f"/api/v1/resumes/{resume_id}/analyze?refresh=true",
        headers=headers,
    )
    assert response.status_code == 200
    mock_analyze.assert_called_once()


@patch(
    "services.resume_analysis_service.analyze_resume_text",
    side_effect=GeminiConfigurationError("GEMINI_API_KEY is not configured"),
)
def test_analyze_missing_gemini_config(_mock_analyze, analysis_client):
    client, _, __, headers, resume_id = analysis_client
    response = client.post(
        f"/api/v1/resumes/{resume_id}/analyze",
        headers=headers,
    )
    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.json()["detail"]


@patch(
    "services.resume_analysis_service.analyze_resume_text",
    side_effect=GeminiResponseError("invalid structure"),
)
def test_analyze_invalid_model_output(_mock_analyze, analysis_client):
    client, _, __, headers, resume_id = analysis_client
    response = client.post(
        f"/api/v1/resumes/{resume_id}/analyze",
        headers=headers,
    )
    assert response.status_code == 502


def test_get_analysis_not_found(analysis_client):
    client, _, analysis_repo, headers, resume_id = analysis_client
    analysis_repo.find_latest_for_resume = AsyncMock(return_value=None)
    response = client.get(
        f"/api/v1/resumes/{resume_id}/analysis",
        headers=headers,
    )
    assert response.status_code == 404
