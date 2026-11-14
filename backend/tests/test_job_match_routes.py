from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from core.dependencies import (
    get_analysis_repository,
    get_billing_repository,
    get_job_match_repository,
    get_resume_repository,
    get_session_repository,
    get_user_repository,
)
from tests.fake_billing_repository import FakeBillingRepository
from core.security.jwt import create_access_token
from schemas.job_match_schema import GeminiJobMatchPayload, SkillAlignmentItem
from tests.test_auth_routes import InMemorySessionRepository


@pytest.fixture
def job_match_client(client: TestClient, sample_user_document: dict):
    job_match_repo = AsyncMock()
    job_match_repo.list_by_user = AsyncMock(return_value=[])
    job_match_repo.find_by_id_for_user = AsyncMock(return_value=None)
    job_match_repo.create_match = AsyncMock()

    resume_repo = AsyncMock()
    analysis_repo = AsyncMock()
    user_repo = AsyncMock()
    user_repo.find_by_id = AsyncMock(return_value=sample_user_document)

    from app.main import app

    session_repo = InMemorySessionRepository()
    billing_repo = FakeBillingRepository()
    billing_repo.set_plan(str(sample_user_document["_id"]), "pro")
    app.dependency_overrides[get_billing_repository] = lambda: billing_repo
    app.dependency_overrides[get_job_match_repository] = lambda: job_match_repo
    app.dependency_overrides[get_resume_repository] = lambda: resume_repo
    app.dependency_overrides[get_analysis_repository] = lambda: analysis_repo
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo

    token, _, _ = create_access_token(
        str(sample_user_document["_id"]),
        sample_user_document["email"],
    )
    headers = {"Authorization": f"Bearer {token}"}
    user_id = str(sample_user_document["_id"])

    yield client, job_match_repo, resume_repo, analysis_repo, headers, user_id

    app.dependency_overrides.clear()


@patch("services.job_match_service.analyze_job_match_with_gemini")
def test_create_job_match_success(mock_gemini, job_match_client):
    client, job_match_repo, resume_repo, analysis_repo, headers, user_id = job_match_client
    resume_id = "507f1f77bcf86cd799439033"
    now = datetime.now(timezone.utc)

    resume_repo.find_by_id_for_user = AsyncMock(
        return_value={
            "_id": ObjectId(resume_id),
            "user_id": user_id,
            "extracted_text": "Python developer with FastAPI experience.",
        }
    )
    analysis_repo.find_latest_for_resume = AsyncMock(
        return_value={
            "_id": ObjectId(),
            "user_id": user_id,
            "resume_id": resume_id,
            "status": "completed",
            "analysis": {
                "professional_summary": "Backend engineer",
                "skills": ["Python", "FastAPI"],
                "experience_analysis": "Built APIs",
            },
        }
    )

    mock_gemini.return_value = GeminiJobMatchPayload(
        job_title_inferred="Backend Engineer",
        required_skills=["Python", "FastAPI"],
        preferred_skills=["Kubernetes"],
        skill_alignments=[
            SkillAlignmentItem(
                skill="Python",
                requirement_type="required",
                match_status="matched",
                resume_evidence="Listed on resume",
                gap_explanation="",
            ),
            SkillAlignmentItem(
                skill="Kubernetes",
                requirement_type="preferred",
                match_status="not_evidenced",
                resume_evidence="",
                gap_explanation="Not listed",
            ),
        ],
        gap_summary="Add orchestration experience",
        strengths_for_role=["Strong Python backend"],
        interview_questions=[
            {
                "question": "Describe a FastAPI service you built?",
                "category": "technical",
                "difficulty": "intermediate",
                "relevance": "FastAPI",
                "evaluates": "Backend depth",
            },
            {
                "question": "How do you deploy Python services?",
                "category": "technical",
                "difficulty": "intermediate",
                "relevance": "DevOps",
                "evaluates": "Operations",
            },
            {
                "question": "Tell me about a production incident?",
                "category": "behavioral",
                "difficulty": "intermediate",
                "relevance": "Reliability",
                "evaluates": "STAR",
            },
        ],
    )

    saved_id = ObjectId("507f1f77bcf86cd799439044")

    async def _create(document):
        document["_id"] = saved_id
        document["created_at"] = now
        document["updated_at"] = now
        return document

    job_match_repo.create_match = AsyncMock(side_effect=_create)

    response = client.post(
        "/api/v1/job-matches",
        headers=headers,
        json={
            "resume_id": resume_id,
            "job_description": "We need a Python FastAPI engineer with cloud skills. "
            * 3,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["resume_id"] == resume_id
    assert body["score"]["match_score"] >= 0
    assert len(body["interview_questions"]) >= 3


def test_create_job_match_requires_analysis(job_match_client):
    client, _job_match_repo, resume_repo, analysis_repo, headers, user_id = job_match_client
    resume_id = "507f1f77bcf86cd799439033"
    resume_repo.find_by_id_for_user = AsyncMock(
        return_value={
            "_id": ObjectId(resume_id),
            "user_id": user_id,
            "extracted_text": "Text",
        }
    )
    analysis_repo.find_latest_for_resume = AsyncMock(return_value=None)

    response = client.post(
        "/api/v1/job-matches",
        headers=headers,
        json={
            "resume_id": resume_id,
            "job_description": "Role requires Python and system design skills for backend. "
            * 4,
        },
    )
    assert response.status_code == 422
