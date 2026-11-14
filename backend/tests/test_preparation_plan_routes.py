from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from core.dependencies import (
    get_analysis_repository,
    get_billing_repository,
    get_interview_repository,
    get_job_match_repository,
    get_preparation_plan_repository,
    get_resume_repository,
    get_session_repository,
    get_user_repository,
)
from tests.fake_billing_repository import FakeBillingRepository
from core.security.jwt import create_access_token
from schemas.preparation_plan_schema import GeminiPlanDayPayload, GeminiSevenDayPlanPayload
from tests.test_auth_routes import InMemorySessionRepository


def _seven_day_payload() -> GeminiSevenDayPlanPayload:
    return GeminiSevenDayPlanPayload(
        plan_summary="Personalised week focused on Python and STAR stories.",
        priority_gaps=["Kubernetes", "STAR results"],
        days=[
            GeminiPlanDayPayload(
                day_number=n,
                learning_objective=f"Day {n} objective",
                skills_to_practice=["Python"],
                learning_activities=["Study", "Notes"],
                interview_questions=["Q1?", "Q2?"],
                practical_exercise="Exercise" if n % 2 == 0 else None,
                estimated_duration_minutes=45,
                completion_criteria="Completed practice",
            )
            for n in range(1, 8)
        ],
    )


@pytest.fixture
def plan_client(client: TestClient, sample_user_document: dict):
    plan_repo = AsyncMock()
    plan_repo.list_by_user = AsyncMock(return_value=[])
    plan_repo.find_by_id_for_user = AsyncMock(return_value=None)
    plan_repo.create_plan = AsyncMock()
    plan_repo.archive_plan = AsyncMock()
    plan_repo.update_task_completion = AsyncMock()

    resume_repo = AsyncMock()
    analysis_repo = AsyncMock()
    job_match_repo = AsyncMock()
    interview_repo = AsyncMock()

    user_repo = AsyncMock()
    user_repo.find_by_id = AsyncMock(return_value=sample_user_document)

    from app.main import app

    session_repo = InMemorySessionRepository()
    billing_repo = FakeBillingRepository()
    billing_repo.set_plan(str(sample_user_document["_id"]), "pro")
    app.dependency_overrides[get_billing_repository] = lambda: billing_repo
    app.dependency_overrides[get_preparation_plan_repository] = lambda: plan_repo
    app.dependency_overrides[get_resume_repository] = lambda: resume_repo
    app.dependency_overrides[get_analysis_repository] = lambda: analysis_repo
    app.dependency_overrides[get_job_match_repository] = lambda: job_match_repo
    app.dependency_overrides[get_interview_repository] = lambda: interview_repo
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
        plan_repo,
        resume_repo,
        analysis_repo,
        interview_repo,
        headers,
        user_id,
    )

    app.dependency_overrides.clear()


@patch("services.preparation_plan_service.run_preparation_plan_workflow")
def test_generate_plan_success(mock_workflow, plan_client):
    (
        client,
        plan_repo,
        resume_repo,
        analysis_repo,
        interview_repo,
        headers,
        user_id,
    ) = plan_client
    resume_id = "507f1f77bcf86cd799439055"
    now = datetime.now(timezone.utc)

    resume_repo.find_by_id_for_user = AsyncMock(
        return_value={"_id": ObjectId(resume_id), "user_id": user_id}
    )
    analysis_repo.find_latest_for_resume = AsyncMock(
        return_value={
            "_id": ObjectId(),
            "status": "completed",
            "analysis": {
                "professional_summary": "Engineer",
                "skills": ["Python"],
                "role_recommendations": ["Backend Engineer"],
                "skill_gaps": ["K8s"],
            },
        }
    )
    interview_repo.list_completed_by_user = AsyncMock(return_value=[])
    mock_workflow.return_value = {
        "status": "completed",
        "plan": _seven_day_payload(),
    }

    saved_id = ObjectId("507f1f77bcf86cd799439066")

    async def _create(document):
        document["_id"] = saved_id
        document["created_at"] = now
        document["updated_at"] = now
        return document

    plan_repo.create_plan = AsyncMock(side_effect=_create)

    response = client.post(
        "/api/v1/preparation-plans",
        headers=headers,
        json={
            "resume_id": resume_id,
            "daily_study_minutes": 60,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["resume_id"] == resume_id
    assert len(body["days"]) == 7
    assert body["tasks_total"] > 0


@patch("services.preparation_plan_service.run_preparation_plan_workflow")
def test_generate_plan_insufficient_evidence(mock_workflow, plan_client):
    client, _plan_repo, resume_repo, analysis_repo, _interview, headers, user_id = plan_client
    resume_id = "507f1f77bcf86cd799439055"
    resume_repo.find_by_id_for_user = AsyncMock(
        return_value={"_id": ObjectId(resume_id), "user_id": user_id}
    )
    analysis_repo.find_latest_for_resume = AsyncMock(
        return_value={
            "_id": ObjectId(),
            "status": "completed",
            "analysis": {"professional_summary": "x", "skills": ["a"]},
        }
    )
    _interview.list_completed_by_user = AsyncMock(return_value=[])
    mock_workflow.return_value = {
        "status": "insufficient_data",
        "message": "Not enough evidence",
        "plan": None,
    }

    response = client.post(
        "/api/v1/preparation-plans",
        headers=headers,
        json={"resume_id": resume_id, "daily_study_minutes": 45},
    )
    assert response.status_code == 422


def test_update_task_ownership(plan_client):
    client, plan_repo, _r, _a, _i, headers, user_id = plan_client
    plan_id = "507f1f77bcf86cd799439077"
    now = datetime.now(timezone.utc)
    plan_doc = {
        "_id": ObjectId(plan_id),
        "user_id": user_id,
        "resume_id": "r",
        "status": "active",
        "daily_study_minutes": 45,
        "model": "test",
        "plan_start_date": now.date().isoformat(),
        "created_at": now,
        "updated_at": now,
        "plan_summary": "s",
        "priority_gaps": [],
        "days": [
            {
                "day_number": 1,
                "relative_label": "Day 1",
                "scheduled_date": now.date().isoformat(),
                "theme": "Gaps",
                "learning_objective": "o",
                "skills_to_practice": ["x"],
                "learning_activities": ["a"],
                "interview_questions": ["q"],
                "practical_exercise": None,
                "estimated_duration_minutes": 45,
                "completion_criteria": "c",
                "day_completed": False,
                "tasks": [
                    {
                        "task_id": "d1-learn-1",
                            "title": "Task one",
                        "description": "d",
                        "task_type": "learning",
                        "estimated_minutes": 15,
                        "completed": True,
                        "completed_at": now.isoformat(),
                    }
                ],
            }
        ],
    }
    plan_repo.update_task_completion = AsyncMock(return_value=plan_doc)

    response = client.patch(
        f"/api/v1/preparation-plans/{plan_id}/days/1/tasks/d1-learn-1",
        headers=headers,
        json={"completed": True},
    )
    assert response.status_code == 200
    assert response.json()["tasks_completed"] >= 1


def test_generate_requires_analysed_resume(plan_client):
    client, _plan, resume_repo, analysis_repo, _i, headers, user_id = plan_client
    resume_id = "507f1f77bcf86cd799439055"
    resume_repo.find_by_id_for_user = AsyncMock(
        return_value={"_id": ObjectId(resume_id), "user_id": user_id}
    )
    analysis_repo.find_latest_for_resume = AsyncMock(return_value=None)

    response = client.post(
        "/api/v1/preparation-plans",
        headers=headers,
        json={"resume_id": resume_id, "daily_study_minutes": 45},
    )
    assert response.status_code == 422


@patch("services.preparation_plan_service.run_preparation_plan_workflow")
def test_regenerate_plan_success(mock_workflow, plan_client):
    (
        client,
        plan_repo,
        resume_repo,
        analysis_repo,
        interview_repo,
        headers,
        user_id,
    ) = plan_client
    plan_id = "507f1f77bcf86cd799439077"
    resume_id = "507f1f77bcf86cd799439055"
    now = datetime.now(timezone.utc)

    plan_repo.find_by_id_for_user = AsyncMock(
        return_value={
            "_id": ObjectId(plan_id),
            "user_id": user_id,
            "resume_id": resume_id,
            "daily_study_minutes": 45,
            "status": "active",
        }
    )
    resume_repo.find_by_id_for_user = AsyncMock(
        return_value={"_id": ObjectId(resume_id), "user_id": user_id}
    )
    analysis_repo.find_latest_for_resume = AsyncMock(
        return_value={
            "_id": ObjectId(),
            "status": "completed",
            "analysis": {
                "professional_summary": "Engineer",
                "skills": ["Python"],
                "role_recommendations": ["Backend Engineer"],
                "skill_gaps": ["K8s"],
            },
        }
    )
    interview_repo.list_completed_by_user = AsyncMock(return_value=[])
    mock_workflow.return_value = {
        "status": "completed",
        "plan": _seven_day_payload(),
    }

    async def _create(document):
        document["_id"] = ObjectId("507f1f77bcf86cd799439088")
        document["created_at"] = now
        document["updated_at"] = now
        return document

    plan_repo.create_plan = AsyncMock(side_effect=_create)
    plan_repo.archive_plan = AsyncMock(return_value=True)

    response = client.post(
        f"/api/v1/preparation-plans/{plan_id}/regenerate",
        headers=headers,
    )
    assert response.status_code == 201
    assert len(response.json()["days"]) == 7
