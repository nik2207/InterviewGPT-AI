from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from core.dependencies import (
    get_billing_repository,
    get_interview_repository,
    get_session_repository,
    get_user_repository,
)
from tests.fake_billing_repository import FakeBillingRepository
from core.security.jwt import create_access_token
from services.interview_report_pdf import generate_interview_report_pdf
from tests.fixtures_interview import sample_evaluation
from tests.test_auth_routes import InMemorySessionRepository
from tests.test_interview_routes import FakeInterviewRepository, _session_doc


@pytest.fixture
def history_client(client: TestClient, sample_user_document: dict):
    interview_repo = FakeInterviewRepository()
    user_repo = AsyncMock()
    user_repo.find_by_id = AsyncMock(return_value=sample_user_document)

    from app.main import app

    session_repo = InMemorySessionRepository()
    billing_repo = FakeBillingRepository()
    billing_repo.set_plan(str(sample_user_document["_id"]), "pro")
    app.dependency_overrides[get_billing_repository] = lambda: billing_repo
    app.dependency_overrides[get_interview_repository] = lambda: interview_repo
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo

    token, _, _ = create_access_token(
        str(sample_user_document["_id"]),
        sample_user_document["email"],
    )
    headers = {"Authorization": f"Bearer {token}"}

    yield client, interview_repo, headers, str(sample_user_document["_id"])
    app.dependency_overrides.clear()


def _completed_session(user_id: str) -> dict:
    doc = _session_doc(user_id)
    evaluation = sample_evaluation().model_dump()
    doc["status"] = "completed"
    doc["completed_at"] = datetime.now(timezone.utc)
    doc["current_question_index"] = 3
    doc["answers"] = [
        {
            "question_id": f"q{i}",
            "submission_id": f"subcomplete{i:02d}",
            "answer_text": "Answer text here.",
            "submitted_at": datetime.now(timezone.utc),
            "evaluation_status": "evaluated",
            "evaluation": evaluation,
            "evaluated_at": datetime.now(timezone.utc),
            "evaluation_error": None,
        }
        for i in range(1, 4)
    ]
    doc["summary"] = {
        "total_questions": 3,
        "answered_questions": 3,
        "average_score": 80.0,
        "highlights": ["Clear communication"],
        "focus_areas": ["Add metrics"],
    }
    return doc


def test_history_empty(history_client):
    client, interview_repo, headers, _user_id = history_client
    interview_repo.list_completed_by_user = AsyncMock(return_value=[])

    response = client.get("/api/v1/interviews/history", headers=headers)
    assert response.status_code == 200
    assert response.json()["interviews"] == []


def test_history_lists_completed(history_client):
    client, interview_repo, headers, user_id = history_client
    doc = _completed_session(user_id)
    interview_repo.list_completed_by_user = AsyncMock(return_value=[doc])

    response = client.get("/api/v1/interviews/history", headers=headers)
    assert response.status_code == 200
    body = response.json()["interviews"]
    assert len(body) == 1
    assert body[0]["role"] == "Backend Engineer"
    assert body[0]["question_count"] == 3
    assert body[0]["overall_score"] == 80.0


def test_report_requires_ownership(history_client):
    client, interview_repo, headers, _user_id = history_client
    interview_repo.find_by_id_for_user = AsyncMock(return_value=None)

    response = client.get(
        "/api/v1/interviews/507f1f77bcf86cd799439020/report",
        headers=headers,
    )
    assert response.status_code == 404


def test_report_pdf_success(history_client):
    client, interview_repo, headers, user_id = history_client
    doc = _completed_session(user_id)
    interview_repo.find_by_id_for_user = AsyncMock(return_value=doc)

    response = client.get(
        f"/api/v1/interviews/{doc['_id']}/report",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 100
    assert response.content.startswith(b"%PDF")


def test_report_incomplete_session_rejected(history_client):
    client, interview_repo, headers, user_id = history_client
    doc = _session_doc(user_id)
    interview_repo.find_by_id_for_user = AsyncMock(return_value=doc)

    response = client.get(
        f"/api/v1/interviews/{doc['_id']}/report",
        headers=headers,
    )
    assert response.status_code == 422


def test_generate_pdf_with_missing_evaluation():
    doc = {
        "role": "Engineer",
        "completed_at": datetime.now(timezone.utc),
        "summary": {"total_questions": 1, "average_score": None},
        "questions": [{"id": "q1", "question": "What is REST?"}],
        "answers": [
            {
                "question_id": "q1",
                "answer_text": "REST is an architectural style.",
                "evaluation": None,
            }
        ],
    }
    pdf = generate_interview_report_pdf(doc)
    assert pdf.startswith(b"%PDF")
