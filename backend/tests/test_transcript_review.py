from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from core.dependencies import get_interview_repository, get_session_repository, get_user_repository
from core.security.jwt import create_access_token
from services.transcript_review_service import build_transcript_review
from tests.test_auth_routes import InMemorySessionRepository
from tests.test_interview_routes import FakeInterviewRepository


def _completed_doc(user_id: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "_id": ObjectId("507f1f77bcf86cd799439030"),
        "user_id": user_id,
        "role": "Backend Engineer",
        "difficulty": "intermediate",
        "interview_type": "mixed",
        "status": "completed",
        "completed_at": now,
        "questions": [
            {
                "id": "q1",
                "question": "Explain caching?",
                "category": "technical",
                "difficulty": "intermediate",
                "relevance": "System design",
                "evaluates": "Depth",
            },
            {
                "id": "q2",
                "question": "Skipped follow-up",
                "category": "technical",
                "difficulty": "intermediate",
                "relevance": "System design",
                "evaluates": "Depth",
                "is_follow_up": True,
                "parent_question_id": "q1",
                "skipped": True,
            },
            {
                "id": "q3",
                "question": "Leadership example?",
                "category": "behavioral",
                "difficulty": "intermediate",
                "relevance": "Leadership",
                "evaluates": "STAR",
            },
        ],
        "answers": [
            {
                "question_id": "q1",
                "submission_id": "sub1",
                "answer_text": "We use Redis.",
                "submitted_at": now,
                "evaluation_status": "evaluated",
                "evaluation": {
                    "dimension_scores": {
                        "technical_correctness": 2,
                        "relevance": 3,
                        "completeness": 2,
                        "answer_structure": 3,
                    },
                    "strengths": [],
                    "missing_concepts": ["invalidation"],
                    "improvement_suggestions": [],
                    "feedback_summary": "Too brief.",
                    "overall_score": 55.0,
                    "scoring_rules": "rules",
                },
                "evaluated_at": now,
                "evaluation_error": None,
                "speech_metrics": {
                    "input_mode": "speech",
                    "word_count": 4,
                    "duration_seconds": 12.5,
                    "words_per_minute": 19.0,
                    "filler_word_count": 0,
                    "filler_words_used": [],
                    "speech_timing_available": True,
                    "disclaimer": "metrics",
                },
            },
            {
                "question_id": "q3",
                "submission_id": "sub3",
                "answer_text": "Led a migration.",
                "submitted_at": now,
                "evaluation_status": "evaluated",
                "evaluation": {
                    "dimension_scores": {
                        "technical_correctness": 5,
                        "relevance": 5,
                        "completeness": 5,
                        "answer_structure": 5,
                    },
                    "strengths": ["Clear"],
                    "missing_concepts": [],
                    "improvement_suggestions": [],
                    "feedback_summary": "Strong.",
                    "overall_score": 100.0,
                    "scoring_rules": "rules",
                },
                "evaluated_at": now,
                "evaluation_error": None,
            },
        ],
        "review_bookmarks": ["q1"],
        "voice_interview": {
            "enabled": True,
            "tone": "professional",
            "session_status": "ended",
            "transcript": [
                {
                    "role": "interviewer",
                    "text": "Explain caching?",
                    "question_id": "q1",
                    "created_at": now,
                }
            ],
            "disclaimer": "voice",
        },
    }


def test_transcript_ordering_and_weak_highlight():
    doc = _completed_doc("user1")
    review = build_transcript_review(doc, session_id="abc")
    assert [item.sequence for item in review.items] == [1, 2, 3]
    assert review.items[0].answer_status == "answered"
    assert review.items[0].is_weak is True
    assert review.items[0].is_bookmarked is True
    assert review.items[1].answer_status == "skipped"
    assert review.items[1].timing is None
    assert review.items[0].timing is not None
    assert review.items[0].timing.timing_reliable is True
    assert review.items[2].is_weak is False
    assert len(review.items[0].voice_transcript) == 1
    assert review.audio_playback_supported is False
    assert review.items[0].audio_recording_available is False


@pytest.fixture
def transcript_client(client: TestClient, sample_user_document: dict):
    interview_repo = FakeInterviewRepository()
    user_repo = AsyncMock()
    user_repo.find_by_id = AsyncMock(return_value=sample_user_document)

    from app.main import app

    session_repo = InMemorySessionRepository()
    app.dependency_overrides[get_interview_repository] = lambda: interview_repo
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


def test_transcript_review_ownership(transcript_client):
    client, interview_repo, headers, user_id = transcript_client
    doc = _completed_doc(user_id)
    session_id = str(doc["_id"])
    interview_repo.find_by_id_for_user = AsyncMock(return_value=doc)

    response = client.get(
        f"/api/v1/interviews/{session_id}/transcript/review",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["is_weak"] is True
    assert body["audio_playback_supported"] is False


def test_transcript_review_not_found(transcript_client):
    client, interview_repo, headers, _user_id = transcript_client
    interview_repo.find_by_id_for_user = AsyncMock(return_value=None)

    response = client.get(
        "/api/v1/interviews/507f1f77bcf86cd799439030/transcript/review",
        headers=headers,
    )
    assert response.status_code == 404


def test_transcript_bookmarks_update(transcript_client):
    client, interview_repo, headers, user_id = transcript_client
    doc = _completed_doc(user_id)
    session_id = str(doc["_id"])
    interview_repo.find_by_id_for_user = AsyncMock(return_value=doc)
    updated = {**doc, "review_bookmarks": ["q1", "q3"]}
    interview_repo.set_review_bookmarks = AsyncMock(return_value=updated)

    response = client.patch(
        f"/api/v1/interviews/{session_id}/transcript/bookmarks",
        headers=headers,
        json={"question_ids": ["q1", "q3", "invalid"]},
    )
    assert response.status_code == 200
    assert set(response.json()["bookmarks"]) == {"q1", "q3"}


def test_transcript_export_pdf(transcript_client):
    client, interview_repo, headers, user_id = transcript_client
    doc = _completed_doc(user_id)
    session_id = str(doc["_id"])
    interview_repo.find_by_id_for_user = AsyncMock(return_value=doc)

    response = client.get(
        f"/api/v1/interviews/{session_id}/transcript/export",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 100


def test_delete_interview_session(transcript_client):
    client, interview_repo, headers, user_id = transcript_client
    interview_repo.delete_session_for_user = AsyncMock(return_value=True)

    response = client.delete(
        "/api/v1/interviews/507f1f77bcf86cd799439030",
        headers=headers,
    )
    assert response.status_code == 204


def test_delete_interview_wrong_owner(transcript_client):
    client, interview_repo, headers, _user_id = transcript_client
    interview_repo.delete_session_for_user = AsyncMock(return_value=False)

    response = client.delete(
        "/api/v1/interviews/507f1f77bcf86cd799439030",
        headers=headers,
    )
    assert response.status_code == 404
