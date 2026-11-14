from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

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
from schemas.company_prep_schema import (
    ChecklistItem,
    CompanyPrepQuestion,
)
from services.company_catalogue_service import get_company, list_companies
from tests.test_auth_routes import InMemorySessionRepository


class FakeCompanyPrepRepository:
    def __init__(self) -> None:
        self.create_prep = AsyncMock()
        self.find_by_id_for_user = AsyncMock(return_value=None)
        self.list_by_user = AsyncMock(return_value=[])
        self.update_checklist = AsyncMock()
        self.link_interview_session = AsyncMock()


def _sample_questions() -> list[CompanyPrepQuestion]:
    return [
        CompanyPrepQuestion(
            id=f"q{i}",
            question=f"Practice question {i} for this role?",
            prep_category="technical",
            difficulty="intermediate",
            relevance="Role practice",
            evaluates="Depth",
            source_type="ai_generated_practice",
            source_label="AI practice generator",
        )
        for i in range(1, 6)
    ]


def _sample_checklist() -> list[ChecklistItem]:
    return [
        ChecklistItem(
            id="c1",
            label="Review public careers page",
            prep_category="general",
            completed=False,
            source_type="catalogue_public",
            source_label="https://careers.example",
        )
    ]


@pytest.fixture
def company_prep_client(client: TestClient, sample_user_document: dict):
    prep_repo = FakeCompanyPrepRepository()
    interview_repo = AsyncMock()

    from app.main import app
    from tests.test_interview_routes import FakeInterviewRepository

    interview_repo = FakeInterviewRepository()
    user_repo = AsyncMock()
    user_repo.find_by_id = AsyncMock(return_value=sample_user_document)

    session_repo = InMemorySessionRepository()
    app.dependency_overrides[get_company_prep_repository] = lambda: prep_repo
    app.dependency_overrides[get_interview_repository] = lambda: interview_repo
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo

    token, _, _ = create_access_token(
        str(sample_user_document["_id"]),
        sample_user_document["email"],
    )
    headers = {"Authorization": f"Bearer {token}"}
    user_id = str(sample_user_document["_id"])

    yield client, prep_repo, interview_repo, headers, user_id
    app.dependency_overrides.clear()


def test_catalogue_lists_google():
    result = list_companies("google")
    assert any(c.id == "google" for c in result.companies)
    assert result.disclaimer


def test_get_company_not_found_raises_in_service():
    assert get_company("not-a-real-id") is None


def test_list_companies_requires_auth(client: TestClient):
    response = client.get("/api/v1/company-prep/companies")
    assert response.status_code == 401


def test_list_companies_with_auth(company_prep_client):
    client, _, _, headers, _ = company_prep_client
    response = client.get("/api/v1/company-prep/companies?q=amazon", headers=headers)
    assert response.status_code == 200
    names = [c["name"] for c in response.json()["companies"]]
    assert "Amazon" in names


@patch("services.company_prep_service.generate_company_prep_content")
def test_create_preparation_persists(mock_generate, company_prep_client):
    client, prep_repo, _, headers, user_id = company_prep_client
    mock_generate.return_value = (_sample_questions(), _sample_checklist())

    now = datetime.now(timezone.utc)
    saved = {
        "_id": ObjectId("507f1f77bcf86cd799439040"),
        "user_id": user_id,
        "company_id": "google",
        "company_name": "Google",
        "job_role": "Software Engineer",
        "experience_level": "mid",
        "categories": ["technical", "coding"],
        "user_notes": None,
        "questions": [q.model_dump() for q in _sample_questions()],
        "checklist": [c.model_dump() for c in _sample_checklist()],
        "interview_session_id": None,
        "created_at": now,
        "updated_at": now,
    }
    prep_repo.create_prep = AsyncMock(return_value=saved)

    response = client.post(
        "/api/v1/company-prep/preparations",
        headers=headers,
        json={
            "company_id": "google",
            "job_role": "Software Engineer",
            "experience_level": "mid",
            "categories": ["technical", "coding"],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["company"]["id"] == "google"
    assert all(
        q["source_type"] == "ai_generated_practice" for q in body["questions"]
    )
    assert COMPANY_PREP_DISCLAIMER_FRAGMENT in body["disclaimer"]


COMPANY_PREP_DISCLAIMER_FRAGMENT = "not actual"


def test_get_preparation_ownership(company_prep_client):
    client, prep_repo, _, headers, user_id = company_prep_client
    now = datetime.now(timezone.utc)
    doc = {
        "_id": ObjectId("507f1f77bcf86cd799439041"),
        "user_id": user_id,
        "company_id": "google",
        "company_name": "Google",
        "job_role": "SDE",
        "experience_level": "mid",
        "categories": ["technical"],
        "questions": [q.model_dump() for q in _sample_questions()],
        "checklist": [c.model_dump() for c in _sample_checklist()],
        "created_at": now,
        "updated_at": now,
    }
    prep_repo.find_by_id_for_user = AsyncMock(return_value=doc)

    response = client.get(
        "/api/v1/company-prep/preparations/507f1f77bcf86cd799439041",
        headers=headers,
    )
    assert response.status_code == 200


def test_get_preparation_not_found(company_prep_client):
    client, prep_repo, _, headers, _ = company_prep_client
    prep_repo.find_by_id_for_user = AsyncMock(return_value=None)

    response = client.get(
        "/api/v1/company-prep/preparations/507f1f77bcf86cd799439041",
        headers=headers,
    )
    assert response.status_code == 404


@patch("services.company_prep_service.create_interview_session")
def test_start_mock_interview(mock_create, company_prep_client):
    client, prep_repo, interview_repo, headers, user_id = company_prep_client
    now = datetime.now(timezone.utc)
    prep_id = "507f1f77bcf86cd799439042"
    doc = {
        "_id": ObjectId(prep_id),
        "user_id": user_id,
        "company_id": "microsoft",
        "company_name": "Microsoft",
        "job_role": "Backend Engineer",
        "experience_level": "mid",
        "categories": ["technical", "behavioural"],
        "questions": [q.model_dump() for q in _sample_questions()],
        "checklist": [],
        "created_at": now,
        "updated_at": now,
    }
    prep_repo.find_by_id_for_user = AsyncMock(return_value=doc)
    prep_repo.link_interview_session = AsyncMock(return_value=doc)

    from schemas.interview_schema import InterviewSessionResponse, InterviewSessionSummary

    mock_create.return_value = InterviewSessionResponse(
        id="interview123456",
        user_id=user_id,
        role="Backend Engineer — Microsoft prep",
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

    response = client.post(
        f"/api/v1/company-prep/preparations/{prep_id}/start-interview",
        headers=headers,
        json={"question_count": 5},
    )
    assert response.status_code == 200
    assert response.json()["interview_session_id"] == "interview123456"
    mock_create.assert_awaited_once()
