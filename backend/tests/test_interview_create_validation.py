from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from core.dependencies import (
    get_analysis_repository,
    get_interview_repository,
    get_resume_repository,
    get_session_repository,
    get_user_repository,
)
from core.security.jwt import create_access_token
from tests.test_auth_routes import InMemorySessionRepository
from tests.test_interview_routes import FakeInterviewRepository


@pytest.fixture
def create_client(client: TestClient, sample_user_document: dict):
    interview_repo = FakeInterviewRepository()
    resume_repo = AsyncMock()
    analysis_repo = AsyncMock()
    user_repo = AsyncMock()
    user_repo.find_by_id = AsyncMock(return_value=sample_user_document)

    from app.main import app

    session_repo = InMemorySessionRepository()
    app.dependency_overrides[get_interview_repository] = lambda: interview_repo
    app.dependency_overrides[get_resume_repository] = lambda: resume_repo
    app.dependency_overrides[get_analysis_repository] = lambda: analysis_repo
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo

    token, _, _ = create_access_token(
        str(sample_user_document["_id"]),
        sample_user_document["email"],
    )
    headers = {"Authorization": f"Bearer {token}"}
    resume_id = "507f1f77bcf86cd799439012"

    yield client, resume_repo, analysis_repo, headers, resume_id
    app.dependency_overrides.clear()


def test_create_resume_interview_insufficient_analyzed_questions(create_client):
    client, resume_repo, analysis_repo, headers, resume_id = create_client
    resume_repo.find_by_id_for_user = AsyncMock(
        return_value={"_id": ObjectId(resume_id), "user_id": "u"}
    )
    analysis_repo.find_latest_for_resume = AsyncMock(
        return_value={
            "interview_questions": [
                {
                    "question": "Only one question here?",
                    "category": "technical",
                    "difficulty": "intermediate",
                    "relevance": "Python",
                    "evaluates": "Depth",
                },
                {
                    "question": "Second question here?",
                    "category": "technical",
                    "difficulty": "intermediate",
                    "relevance": "Python",
                    "evaluates": "Depth",
                },
            ]
        }
    )

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "role": "Backend Engineer",
            "difficulty": "intermediate",
            "interview_type": "resume_based",
            "resume_id": resume_id,
            "question_count": 5,
        },
    )
    assert response.status_code == 422
    assert "3 questions" in response.json()["detail"]
