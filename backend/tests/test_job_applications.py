from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from core.dependencies import (
    get_job_application_repository,
    get_session_repository,
    get_user_repository,
)
from core.security.jwt import create_access_token
from repositories.job_application_repository import JobApplicationDuplicateError
from tests.test_auth_routes import InMemorySessionRepository


class FakeJobApplicationRepository:
    def __init__(self) -> None:
        self.create_application = AsyncMock()
        self.find_by_id_for_user = AsyncMock(return_value=None)
        self.list_applications = AsyncMock(return_value=([], 0))
        self.list_all_for_user = AsyncMock(return_value=[])
        self.update_application = AsyncMock()
        self.delete_application = AsyncMock(return_value=True)
        self.link_interview_session = AsyncMock()


@pytest.fixture
def applications_client(client: TestClient, sample_user_document: dict):
    app_repo = FakeJobApplicationRepository()
    user_repo = AsyncMock()
    user_repo.find_by_id = AsyncMock(return_value=sample_user_document)

    from app.main import app

    session_repo = InMemorySessionRepository()
    app.dependency_overrides[get_job_application_repository] = lambda: app_repo
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo

    token, _, _ = create_access_token(
        str(sample_user_document["_id"]),
        sample_user_document["email"],
    )
    headers = {"Authorization": f"Bearer {token}"}
    user_id = str(sample_user_document["_id"])
    yield client, app_repo, headers, user_id
    app.dependency_overrides.clear()


def _app_doc(user_id: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "_id": ObjectId("507f1f77bcf86cd799439070"),
        "user_id": user_id,
        "company": "Acme Corp",
        "job_title": "Backend Engineer",
        "job_description": "Build APIs",
        "job_posting_url": "https://jobs.example.com/123",
        "location": "Remote",
        "employment_type": "full_time",
        "application_date": datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc),
        "status": "applied",
        "resume_id": None,
        "job_match_id": None,
        "interview_dates": [],
        "notes": "",
        "follow_up_date": None,
        "interview_session_id": None,
        "created_at": now,
        "updated_at": now,
    }


def test_create_application(applications_client):
    client, repo, headers, user_id = applications_client
    repo.create_application = AsyncMock(return_value=_app_doc(user_id))

    response = client.post(
        "/api/v1/applications",
        headers=headers,
        json={
            "company": "Acme Corp",
            "job_title": "Backend Engineer",
            "job_posting_url": "https://jobs.example.com/123",
            "status": "applied",
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "applied"


def test_duplicate_application(applications_client):
    client, repo, headers, _ = applications_client
    repo.create_application = AsyncMock(
        side_effect=JobApplicationDuplicateError("duplicate")
    )

    response = client.post(
        "/api/v1/applications",
        headers=headers,
        json={
            "company": "Acme Corp",
            "job_title": "Backend Engineer",
            "job_posting_url": "https://jobs.example.com/123",
        },
    )
    assert response.status_code == 409


def test_invalid_url(applications_client):
    client, _, headers, _ = applications_client

    response = client.post(
        "/api/v1/applications",
        headers=headers,
        json={
            "company": "Acme",
            "job_title": "Engineer",
            "job_posting_url": "ftp://bad.example",
        },
    )
    assert response.status_code == 422


def test_list_filter_pagination(applications_client):
    client, repo, headers, user_id = applications_client
    doc = _app_doc(user_id)
    repo.list_applications = AsyncMock(return_value=([doc], 1))

    response = client.get(
        "/api/v1/applications?status=applied&page=1&page_size=10&q=Acme",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1


def test_update_status(applications_client):
    client, repo, headers, user_id = applications_client
    doc = _app_doc(user_id)
    updated = {**doc, "status": "interview_scheduled"}
    repo.find_by_id_for_user = AsyncMock(return_value=doc)
    repo.update_application = AsyncMock(return_value=updated)

    response = client.patch(
        "/api/v1/applications/507f1f77bcf86cd799439070",
        headers=headers,
        json={"status": "interview_scheduled"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "interview_scheduled"


def test_ownership_get_not_found(applications_client):
    client, _, headers, _ = applications_client
    response = client.get(
        "/api/v1/applications/507f1f77bcf86cd799439070",
        headers=headers,
    )
    assert response.status_code == 404


def test_stats(applications_client):
    client, repo, headers, user_id = applications_client
    repo.list_all_for_user = AsyncMock(return_value=[_app_doc(user_id)])

    response = client.get("/api/v1/applications/stats", headers=headers)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["by_status"]["applied"] == 1


@patch("services.job_application_service.create_interview_session")
def test_start_practice(mock_create, applications_client):
    client, repo, headers, user_id = applications_client
    repo.find_by_id_for_user = AsyncMock(return_value=_app_doc(user_id))
    repo.link_interview_session = AsyncMock(return_value=_app_doc(user_id))

    from schemas.interview_schema import InterviewSessionResponse

    now = datetime.now(timezone.utc)
    mock_create.return_value = InterviewSessionResponse(
        id="session12345",
        user_id=user_id,
        role="Backend Engineer — Acme Corp",
        difficulty="intermediate",
        interview_type="mixed",
        resume_id=None,
        status="in_progress",
        questions=[],
        current_question_index=0,
        answers=[],
        summary=None,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )

    from core.dependencies import (
        get_analysis_repository,
        get_interview_repository,
        get_job_match_repository,
        get_resume_repository,
    )
    from app.main import app

    app.dependency_overrides[get_interview_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_resume_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_job_match_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_analysis_repository] = lambda: AsyncMock()

    response = client.post(
        "/api/v1/applications/507f1f77bcf86cd799439070/start-practice",
        headers=headers,
        json={"question_count": 3},
    )
    assert response.status_code == 200
    assert response.json()["interview_session_id"] == "session12345"


def test_update_links_resume_and_match(applications_client):
    client, repo, headers, user_id = applications_client
    doc = _app_doc(user_id)
    resume_id = "507f1f77bcf86cd799439033"
    match_id = "507f1f77bcf86cd799439044"
    updated = {**doc, "resume_id": resume_id, "job_match_id": match_id}
    repo.find_by_id_for_user = AsyncMock(return_value=doc)
    repo.update_application = AsyncMock(return_value=updated)

    response = client.patch(
        "/api/v1/applications/507f1f77bcf86cd799439070",
        headers=headers,
        json={"resume_id": resume_id, "job_match_id": match_id},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["resume_id"] == resume_id
    assert body["job_match_id"] == match_id


def test_applications_unauthenticated(client: TestClient):
    response = client.get("/api/v1/applications")
    assert response.status_code == 401
