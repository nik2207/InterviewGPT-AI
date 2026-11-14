from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from core.dependencies import (
    get_analysis_repository,
    get_interview_repository,
    get_session_repository,
    get_user_repository,
)
from core.security.jwt import create_access_token
from schemas.coaching_schema import CoachingEvidenceBundle, CoachingEvidenceItem, GeminiCoachingPlanPayload
from tests.test_auth_routes import InMemorySessionRepository
from tests.test_interview_history_report import _completed_session
from tests.test_interview_routes import FakeInterviewRepository
from workflows.coaching_plan_graph import run_coaching_plan_workflow


def _sample_plan() -> GeminiCoachingPlanPayload:
    return GeminiCoachingPlanPayload(
        observed_strengths=["Clear technical explanations"],
        observed_gaps=["Limited metrics in examples"],
        recommended_focus_areas=["Add measurable outcomes to project answers"],
        practice_suggestions=["Practice STAR format for behavioral questions"],
        summary="Focus on quantifying impact while maintaining clear technical depth.",
    )


def test_workflow_success_with_mocked_gemini():
    evidence = CoachingEvidenceBundle(
        user_id="u1",
        session_id="s1",
        role="Backend Engineer",
        session_average_score=80.0,
        items=[
            CoachingEvidenceItem(
                source="interview_session",
                label="Strength",
                observation="Explained API design tradeoffs clearly.",
            )
        ],
    )
    with patch(
        "workflows.coaching_plan_graph.generate_coaching_plan",
        return_value=_sample_plan(),
    ):
        result = run_coaching_plan_workflow(evidence)
    assert result["status"] == "completed"
    assert result["plan"] is not None


def test_workflow_insufficient_evidence():
    result = run_coaching_plan_workflow(None)
    assert result["status"] == "insufficient_data"
    assert result["plan"] is None


def test_workflow_generation_failure():
    evidence = CoachingEvidenceBundle(
        user_id="u1",
        session_id="s1",
        role="Engineer",
        items=[
            CoachingEvidenceItem(
                source="interview_session",
                label="Strength",
                observation="Good answer.",
            )
        ],
    )
    with patch(
        "workflows.coaching_plan_graph.generate_coaching_plan",
        side_effect=Exception("down"),
    ):
        result = run_coaching_plan_workflow(evidence)
    assert result["status"] == "generation_failed"


@pytest.fixture
def coaching_api_client(client: TestClient, sample_user_document: dict):
    interview_repo = FakeInterviewRepository()
    analysis_repo = AsyncMock()
    user_repo = AsyncMock()
    user_repo.find_by_id = AsyncMock(return_value=sample_user_document)

    from app.main import app

    session_repo = InMemorySessionRepository()
    app.dependency_overrides[get_interview_repository] = lambda: interview_repo
    app.dependency_overrides[get_analysis_repository] = lambda: analysis_repo
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo

    token, _, _ = create_access_token(
        str(sample_user_document["_id"]),
        sample_user_document["email"],
    )
    headers = {"Authorization": f"Bearer {token}"}
    user_id = str(sample_user_document["_id"])
    yield client, interview_repo, headers, user_id
    app.dependency_overrides.clear()


@patch("services.coaching_plan_service.run_coaching_plan_workflow")
def test_coaching_plan_endpoint_ownership(mock_run, coaching_api_client):
    client, interview_repo, headers, user_id = coaching_api_client
    doc = _completed_session(user_id)
    interview_repo.find_by_id_for_user = AsyncMock(return_value=doc)
    interview_repo.list_completed_by_user = AsyncMock(return_value=[doc])
    mock_run.return_value = {
        "status": "completed",
        "plan": _sample_plan(),
        "message": None,
    }

    response = client.get(
        f"/api/v1/interviews/{doc['_id']}/coaching-plan",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["plan"]["summary"]


def test_coaching_plan_not_found(coaching_api_client):
    client, interview_repo, headers, _user_id = coaching_api_client
    interview_repo.find_by_id_for_user = AsyncMock(return_value=None)
    response = client.get(
        "/api/v1/interviews/507f1f77bcf86cd799439020/coaching-plan",
        headers=headers,
    )
    assert response.status_code == 404
