from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

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


@pytest.fixture
def voice_client(client: TestClient, sample_user_document: dict):
    interview_repo = AsyncMock()
    interview_repo.find_by_id_for_user = AsyncMock(return_value=None)
    interview_repo.append_voice_transcript = AsyncMock()
    interview_repo.update_voice_session_status = AsyncMock()

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
    user_id = str(sample_user_document["_id"])

    yield client, interview_repo, headers, user_id
    app.dependency_overrides.clear()


def _voice_session(user_id: str, session_id: ObjectId) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "_id": session_id,
        "user_id": user_id,
        "status": "in_progress",
        "role": "Engineer",
        "questions": [
            {
                "id": "q1",
                "question": "Explain REST?",
                "category": "technical",
                "difficulty": "intermediate",
                "relevance": "APIs",
                "evaluates": "Depth",
            }
        ],
        "voice_interview": {
            "enabled": True,
            "tone": "professional",
            "session_status": "active",
            "transcript": [],
            "disclaimer": "Sequential mode.",
        },
        "updated_at": now,
    }


def test_append_transcript_ownership(voice_client):
    client, interview_repo, headers, user_id = voice_client
    session_id = ObjectId("507f1f77bcf86cd799439099")
    doc = _voice_session(user_id, session_id)
    interview_repo.find_by_id_for_user = AsyncMock(return_value=doc)
    interview_repo.append_voice_transcript = AsyncMock(
        return_value={
            **doc,
            "voice_interview": {
                **doc["voice_interview"],
                "transcript": [
                    {
                        "role": "interviewer",
                        "text": "Hello",
                        "question_id": "q1",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                ],
            },
        }
    )

    response = client.post(
        f"/api/v1/interviews/{session_id}/voice/transcript",
        headers=headers,
        json={"role": "interviewer", "text": "Hello", "question_id": "q1"},
    )
    assert response.status_code == 200


@patch("services.voice_interview_service.evaluate_voice_clarification")
def test_clarification_empty_answer(mock_eval, voice_client):
    from schemas.interview_schema import GeminiVoiceClarificationPayload

    client, interview_repo, headers, user_id = voice_client
    session_id = ObjectId("507f1f77bcf86cd799439099")
    doc = _voice_session(user_id, session_id)
    interview_repo.find_by_id_for_user = AsyncMock(return_value=doc)
    mock_eval.return_value = GeminiVoiceClarificationPayload(
        needs_clarification=True,
        interviewer_message="Please add more detail.",
    )
    interview_repo.append_voice_transcript = AsyncMock(return_value=doc)

    response = client.post(
        f"/api/v1/interviews/{session_id}/voice/clarification",
        headers=headers,
        json={"question_id": "q1", "answer_draft": "short"},
    )
    assert response.status_code == 200
    assert response.json()["needs_clarification"] is True
