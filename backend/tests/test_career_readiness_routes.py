from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from core.dependencies import (
    get_analysis_repository,
    get_billing_repository,
    get_career_readiness_repository,
    get_interview_repository,
    get_job_match_repository,
    get_preparation_plan_repository,
    get_resume_repository,
    get_session_repository,
    get_user_repository,
)
from tests.fake_billing_repository import FakeBillingRepository
from core.security.jwt import create_access_token
from tests.fixtures_interview import sample_evaluation
from tests.test_auth_routes import InMemorySessionRepository


@pytest.fixture
def readiness_client(client: TestClient, sample_user_document: dict):
    readiness_repo = AsyncMock()
    readiness_repo.create_report = AsyncMock()
    readiness_repo.list_by_user = AsyncMock(return_value=[])
    readiness_repo.find_by_id_for_user = AsyncMock(return_value=None)

    resume_repo = AsyncMock()
    analysis_repo = AsyncMock()
    job_match_repo = AsyncMock()
    interview_repo = AsyncMock()
    plan_repo = AsyncMock()

    user_repo = AsyncMock()
    user_repo.find_by_id = AsyncMock(return_value=sample_user_document)

    from app.main import app

    session_repo = InMemorySessionRepository()
    billing_repo = FakeBillingRepository()
    billing_repo.set_plan(str(sample_user_document["_id"]), "pro")
    app.dependency_overrides[get_billing_repository] = lambda: billing_repo
    app.dependency_overrides[get_career_readiness_repository] = lambda: readiness_repo
    app.dependency_overrides[get_resume_repository] = lambda: resume_repo
    app.dependency_overrides[get_analysis_repository] = lambda: analysis_repo
    app.dependency_overrides[get_job_match_repository] = lambda: job_match_repo
    app.dependency_overrides[get_interview_repository] = lambda: interview_repo
    app.dependency_overrides[get_preparation_plan_repository] = lambda: plan_repo
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo

    token, _, _ = create_access_token(
        str(sample_user_document["_id"]),
        sample_user_document["email"],
    )
    headers = {"Authorization": f"Bearer {token}"}
    user_id = str(sample_user_document["_id"])

    yield (
        client,
        readiness_repo,
        resume_repo,
        analysis_repo,
        job_match_repo,
        interview_repo,
        plan_repo,
        headers,
        user_id,
    )

    app.dependency_overrides.clear()


def test_generate_readiness_with_interviews(readiness_client):
    (
        client,
        readiness_repo,
        resume_repo,
        analysis_repo,
        job_match_repo,
        interview_repo,
        plan_repo,
        headers,
        user_id,
    ) = readiness_client
    resume_id = "507f1f77bcf86cd799439088"
    match_id = "507f1f77bcf86cd799439089"
    now = datetime.now(timezone.utc)

    resume_repo.find_by_id_for_user = AsyncMock(
        return_value={"_id": ObjectId(resume_id), "user_id": user_id}
    )
    analysis_repo.find_latest_for_resume = AsyncMock(
        return_value={
            "_id": ObjectId(),
            "status": "completed",
            "updated_at": now,
            "analysis": {
                "skills": ["Python"],
                "strengths": ["APIs"],
                "skill_gaps": ["K8s"],
                "role_recommendations": ["Backend Engineer"],
            },
        }
    )
    job_match_repo.find_by_id_for_user = AsyncMock(
        return_value={
            "_id": ObjectId(match_id),
            "user_id": user_id,
            "resume_id": resume_id,
            "job_title": "Backend Engineer",
            "updated_at": now,
            "score": {"match_score": 72.5},
            "skill_alignments": [
                {
                    "skill": "Python",
                    "match_status": "matched",
                    "requirement_type": "required",
                }
            ],
            "gap_summary": "Add cloud",
        }
    )
    interview_repo.list_completed_by_user = AsyncMock(
        return_value=[
            {
                "_id": ObjectId(),
                "role": "Backend",
                "completed_at": now,
                "summary": {"average_score": 78.0},
                "answers": [
                    {
                        "evaluation_status": "evaluated",
                        "evaluation": sample_evaluation().model_dump(),
                        "speech_metrics": {
                            "input_mode": "speech",
                            "words_per_minute": 120,
                            "filler_word_count": 2,
                        },
                    }
                ],
                "questions": [],
            }
        ]
    )
    plan_repo.list_by_user = AsyncMock(return_value=[])

    saved_id = ObjectId("507f1f77bcf86cd799439090")

    async def _create(document):
        document["_id"] = saved_id
        return document

    readiness_repo.create_report = AsyncMock(side_effect=_create)

    response = client.post(
        "/api/v1/career-readiness/reports",
        headers=headers,
        json={"resume_id": resume_id, "job_match_id": match_id},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["overall_readiness"]["status"] == "available"
    assert body["resume_job_alignment"]["score"] == 72.5


def test_readiness_pdf_ownership(readiness_client):
    client, readiness_repo, _r, _a, _j, _i, _p, headers, user_id = readiness_client
    report_id = "507f1f77bcf86cd799439091"
    now = datetime.now(timezone.utc)
    readiness_repo.find_by_id_for_user = AsyncMock(
        return_value={
            "_id": ObjectId(report_id),
            "user_id": user_id,
            "resume_id": "r",
            "job_match_id": None,
            "target_role": "Engineer",
            "generated_at": now,
            "data_coverage": {
                "items": [],
                "summary": "1 of 4",
            },
            "overall_readiness": {
                "score": None,
                "status": "insufficient_data",
                "message": "Not enough practice data",
            },
            "resume_job_alignment": {
                "score": None,
                "status": "insufficient_data",
                "detail": "x",
                "sample_size": 0,
            },
            "technical_knowledge": {
                "score": None,
                "status": "insufficient_data",
                "detail": "x",
                "sample_size": 0,
            },
            "answer_relevance": {
                "score": None,
                "status": "insufficient_data",
                "detail": "x",
                "sample_size": 0,
            },
            "answer_completeness": {
                "score": None,
                "status": "insufficient_data",
                "detail": "x",
                "sample_size": 0,
            },
            "answer_structure": {
                "score": None,
                "status": "insufficient_data",
                "detail": "x",
                "sample_size": 0,
            },
            "communication_indicators": {
                "status": "insufficient_data",
                "speech_answer_count": 0,
                "detail": "none",
            },
            "strongest_skills": [],
            "skills_requiring_improvement": [],
            "interview_performance_trends": [],
            "preparation_plan": None,
            "recommended_next_actions": ["Complete a mock interview."],
            "scoring_rules": "rules",
        }
    )
    response = client.get(
        f"/api/v1/career-readiness/reports/{report_id}/pdf",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
