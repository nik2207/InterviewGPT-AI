"""Release 2 cross-tenant and auth checks (voice, transcript, company prep)."""

from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from core.dependencies import (
    get_company_prep_repository,
    get_interview_repository,
    get_session_repository,
    get_user_repository,
)
from core.security.jwt import create_access_token
from tests.test_auth_routes import InMemorySessionRepository


@pytest.fixture
def r2_client(client: TestClient, sample_user_document: dict):
    from app.main import app

    interview_repo = AsyncMock()
    interview_repo.find_by_id_for_user = AsyncMock(return_value=None)

    prep_repo = AsyncMock()
    prep_repo.find_by_id_for_user = AsyncMock(return_value=None)

    user_repo = AsyncMock()
    user_repo.find_by_id = AsyncMock(return_value=sample_user_document)
    session_repo = InMemorySessionRepository()

    app.dependency_overrides[get_interview_repository] = lambda: interview_repo
    app.dependency_overrides[get_company_prep_repository] = lambda: prep_repo
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo

    token, _, _ = create_access_token(
        str(sample_user_document["_id"]),
        sample_user_document["email"],
    )
    headers = {"Authorization": f"Bearer {token}"}
    yield client, headers, interview_repo
    app.dependency_overrides.clear()


def test_voice_transcript_unauthenticated(client: TestClient):
    response = client.post(
        "/api/v1/interviews/507f1f77bcf86cd799439099/voice/transcript",
        json={"role": "candidate", "text": "hello", "question_id": "q1"},
    )
    assert response.status_code == 401


def test_voice_transcript_other_user_404(r2_client):
    client, headers, _repo = r2_client
    sid = "507f1f77bcf86cd799439099"
    response = client.post(
        f"/api/v1/interviews/{sid}/voice/transcript",
        headers=headers,
        json={"role": "candidate", "text": "hello", "question_id": "q1"},
    )
    assert response.status_code == 404


def test_transcript_review_other_user_404(r2_client):
    client, headers, _repo = r2_client
    sid = "507f1f77bcf86cd799439030"
    response = client.get(
        f"/api/v1/interviews/{sid}/transcript/review",
        headers=headers,
    )
    assert response.status_code == 404


def test_company_prep_other_user_404(r2_client):
    client, headers, _repo = r2_client
    prep_id = "507f1f77bcf86cd799439041"
    response = client.get(
        f"/api/v1/company-prep/preparations/{prep_id}",
        headers=headers,
    )
    assert response.status_code == 404


def test_voice_append_rejects_non_voice_session(r2_client):
    client, headers, interview_repo = r2_client
    sid = ObjectId("507f1f77bcf86cd799439099")
    interview_repo.find_by_id_for_user = AsyncMock(
        return_value={
            "_id": sid,
            "user_id": "u",
            "voice_interview": {"enabled": False},
        }
    )
    response = client.post(
        f"/api/v1/interviews/{sid}/voice/transcript",
        headers=headers,
        json={"role": "candidate", "text": "hello", "question_id": "q1"},
    )
    assert response.status_code == 422
