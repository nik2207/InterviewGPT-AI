"""Stage 1 cross-tenant and auth regression checks."""

from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from core.dependencies import (
    get_billing_repository,
    get_career_readiness_repository,
    get_credit_repository,
    get_job_match_repository,
    get_preparation_plan_repository,
    get_resume_repository,
    get_session_repository,
    get_user_repository,
)
from core.security.jwt import create_access_token
from tests.fake_billing_repository import FakeBillingRepository
from tests.fake_credit_repository import FakeCreditRepository
from tests.test_auth_routes import InMemorySessionRepository


@pytest.fixture
def stage1_client(client: TestClient, sample_user_document: dict):
    from app.main import app

    user_repo = AsyncMock()
    user_repo.find_by_id = AsyncMock(return_value=sample_user_document)
    session_repo = InMemorySessionRepository()
    billing_repo = FakeBillingRepository()
    billing_repo.set_plan(str(sample_user_document["_id"]), "pro")
    credit_repo = FakeCreditRepository()

    job_match_repo = AsyncMock()
    job_match_repo.find_by_id_for_user = AsyncMock(return_value=None)

    plan_repo = AsyncMock()
    plan_repo.find_by_id_for_user = AsyncMock(return_value=None)

    readiness_repo = AsyncMock()
    readiness_repo.find_by_id_for_user = AsyncMock(return_value=None)

    resume_repo = AsyncMock()
    resume_repo.find_by_id_for_user = AsyncMock(return_value=None)

    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo
    app.dependency_overrides[get_billing_repository] = lambda: billing_repo
    app.dependency_overrides[get_credit_repository] = lambda: credit_repo
    app.dependency_overrides[get_job_match_repository] = lambda: job_match_repo
    app.dependency_overrides[get_preparation_plan_repository] = lambda: plan_repo
    app.dependency_overrides[get_career_readiness_repository] = lambda: readiness_repo
    app.dependency_overrides[get_resume_repository] = lambda: resume_repo

    token, _, _ = create_access_token(
        str(sample_user_document["_id"]), sample_user_document["email"]
    )
    headers = {"Authorization": f"Bearer {token}"}
    yield client, headers
    app.dependency_overrides.clear()


def test_unauthenticated_job_match_rejected(client: TestClient):
    response = client.post(
        "/api/v1/job-matches",
        json={"resume_id": "x", "job_description": "a" * 80},
    )
    assert response.status_code == 401


def test_job_match_other_user_returns_404(stage1_client):
    client, headers = stage1_client
    foreign_id = "507f1f77bcf86cd799439099"
    response = client.get(f"/api/v1/job-matches/{foreign_id}", headers=headers)
    assert response.status_code == 404


def test_preparation_plan_other_user_returns_404(stage1_client):
    client, headers = stage1_client
    foreign_id = "507f1f77bcf86cd799439088"
    response = client.get(f"/api/v1/preparation-plans/{foreign_id}", headers=headers)
    assert response.status_code == 404


def test_readiness_report_other_user_returns_404(stage1_client):
    client, headers = stage1_client
    foreign_id = "507f1f77bcf86cd799439077"
    response = client.get(
        f"/api/v1/career-readiness/reports/{foreign_id}", headers=headers
    )
    assert response.status_code == 404


def test_resume_other_user_returns_404(stage1_client):
    client, headers = stage1_client
    foreign_id = "507f1f77bcf86cd799439066"
    response = client.get(f"/api/v1/resumes/{foreign_id}", headers=headers)
    assert response.status_code == 404


def test_free_tier_strips_coach_payload():
    from services.entitlement_service import redact_coaching_if_needed

    evaluation = {
        "feedback_summary": "Good answer with more detail available.",
        "improvement_coach": {
            "improved_example_answer": "Long example",
            "action_to_take": "Revise algorithms",
        },
    }
    redacted = redact_coaching_if_needed(evaluation, "free")
    assert redacted["improvement_coach"] is None
    assert "Upgrade to Pro for detailed improvement coaching." in redacted["feedback_summary"]
