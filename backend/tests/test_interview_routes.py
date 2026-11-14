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
from schemas.interview_schema import GeminiFollowUpQuestionPayload
from services.gemini_answer_evaluation_service import AnswerEvaluationUnavailableError
from tests.fixtures_interview import custom_questions_payload, sample_evaluation
from tests.test_auth_routes import InMemorySessionRepository


class FakeInterviewRepository:
    def __init__(self) -> None:
        self.create_session = AsyncMock()
        self.find_by_id_for_user = AsyncMock(return_value=None)
        self.list_by_user = AsyncMock(return_value=[])
        self.list_completed_by_user = AsyncMock(return_value=[])
        self.append_answer_pending = AsyncMock()
        self.update_answer_evaluation = AsyncMock()
        self.advance_question_index = AsyncMock()
        self.insert_follow_up_question = AsyncMock()
        self.skip_follow_up_question = AsyncMock()
        self.set_review_bookmarks = AsyncMock()
        self.upsert_practice_revision = AsyncMock()
        self.delete_session_for_user = AsyncMock()
        self.complete_session = AsyncMock()

    def find_answer_by_submission(self, session, question_id, submission_id):
        for item in session.get("answers", []):
            if (
                item.get("question_id") == question_id
                and item.get("submission_id") == submission_id
            ):
                return item
        return None

    def find_answer_for_question(self, session, question_id):
        for item in reversed(session.get("answers", [])):
            if item.get("question_id") == question_id:
                return item
        return None


@pytest.fixture
def interview_client(client: TestClient, sample_user_document: dict):
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

    yield client, interview_repo, headers, str(sample_user_document["_id"])

    app.dependency_overrides.clear()


def _session_doc(user_id: str, session_id: ObjectId | None = None) -> dict:
    now = datetime.now(timezone.utc)
    questions = [
        {
            "id": f"q{i}",
            "question": f"Question {i}?",
            "category": "technical",
            "difficulty": "intermediate",
            "relevance": "Python",
            "evaluates": "Depth",
        }
        for i in range(1, 4)
    ]
    return {
        "_id": session_id or ObjectId("507f1f77bcf86cd799439020"),
        "user_id": user_id,
        "role": "Backend Engineer",
        "difficulty": "intermediate",
        "interview_type": "mixed",
        "resume_id": None,
        "status": "in_progress",
        "questions": questions,
        "current_question_index": 0,
        "answers": [],
        "summary": None,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
    }


def test_create_interview_requires_auth(client: TestClient):
    response = client.post(
        "/api/v1/interviews",
        json={
            "role": "Backend Engineer",
            "difficulty": "intermediate",
            "interview_type": "mixed",
            "custom_questions": custom_questions_payload(3),
        },
    )
    assert response.status_code == 401


def test_create_interview_rejects_question_count_below_schema_minimum(
    interview_client,
):
    client, _, headers, _user_id = interview_client
    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "role": "Backend Engineer",
            "difficulty": "intermediate",
            "interview_type": "mixed",
            "question_count": 2,
            "custom_questions": custom_questions_payload(3),
        },
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any(
        "question_count" in str(item).lower() or "greater" in str(item).lower()
        for item in (detail if isinstance(detail, list) else [detail])
    )


def test_create_interview_with_custom_questions(interview_client):
    client, interview_repo, headers, user_id = interview_client
    doc = _session_doc(user_id)
    interview_repo.create_session = AsyncMock(return_value=doc)

    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "role": "Backend Engineer",
            "difficulty": "intermediate",
            "interview_type": "mixed",
            "custom_questions": custom_questions_payload(3),
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "in_progress"
    assert len(body["questions"]) == 3


@patch("services.follow_up_service.generate_follow_up_question")
@patch("services.interview_service.evaluate_answer_text")
def test_submit_answer_success(mock_evaluate, mock_follow_up, interview_client):
    client, interview_repo, headers, user_id = interview_client
    doc = _session_doc(user_id)
    session_id = str(doc["_id"])
    interview_repo.find_by_id_for_user = AsyncMock(return_value=doc)
    mock_evaluate.return_value = sample_evaluation()
    mock_follow_up.return_value = GeminiFollowUpQuestionPayload(
        should_ask_follow_up=False,
    )

    after_eval = {**doc}
    after_eval["answers"] = [
        {
            "question_id": "q1",
            "submission_id": "sub00000001",
            "answer_text": "My detailed answer here.",
            "submitted_at": datetime.now(timezone.utc),
            "evaluation_status": "evaluated",
            "evaluation": sample_evaluation().model_dump(),
            "evaluated_at": datetime.now(timezone.utc),
            "evaluation_error": None,
        }
    ]
    after_eval["current_question_index"] = 0
    updated = {**after_eval, "current_question_index": 1}
    interview_repo.append_answer_pending = AsyncMock(return_value=doc)
    interview_repo.update_answer_evaluation = AsyncMock(return_value=after_eval)
    interview_repo.advance_question_index = AsyncMock(return_value=updated)

    response = client.post(
        f"/api/v1/interviews/{session_id}/answers",
        headers=headers,
        json={
            "submission_id": "sub00000001",
            "answer_text": "My detailed answer here.",
        },
    )
    assert response.status_code == 200
    assert response.json()["current_question_index"] == 1
    mock_evaluate.assert_called_once()


def test_submit_empty_answer(interview_client):
    client, interview_repo, headers, user_id = interview_client
    doc = _session_doc(user_id)
    interview_repo.find_by_id_for_user = AsyncMock(return_value=doc)

    response = client.post(
        f"/api/v1/interviews/{doc['_id']}/answers",
        headers=headers,
        json={"submission_id": "subempty01", "answer_text": "   "},
    )
    assert response.status_code == 422


@patch("services.interview_service.evaluate_answer_text")
def test_submit_duplicate_submission_idempotent(mock_evaluate, interview_client):
    client, interview_repo, headers, user_id = interview_client
    doc = _session_doc(user_id)
    doc["answers"] = [
        {
            "question_id": "q1",
            "submission_id": "subdup0001",
            "answer_text": "Same answer",
            "submitted_at": datetime.now(timezone.utc),
            "evaluation_status": "pending",
            "evaluation": None,
            "evaluated_at": None,
            "evaluation_error": None,
        }
    ]
    interview_repo.find_by_id_for_user = AsyncMock(return_value=doc)

    response = client.post(
        f"/api/v1/interviews/{doc['_id']}/answers",
        headers=headers,
        json={"submission_id": "subdup0001", "answer_text": "Same answer"},
    )
    assert response.status_code == 200
    mock_evaluate.assert_not_called()


@patch("services.interview_service.evaluate_answer_text")
def test_submit_model_error_retains_answer(mock_evaluate, interview_client):
    client, interview_repo, headers, user_id = interview_client
    doc = _session_doc(user_id)
    session_id = str(doc["_id"])
    interview_repo.find_by_id_for_user = AsyncMock(return_value=doc)
    interview_repo.append_answer_pending = AsyncMock(return_value=doc)
    mock_evaluate.side_effect = AnswerEvaluationUnavailableError("temporary")

    failed = {**doc}
    failed["answers"] = [
        {
            "question_id": "q1",
            "submission_id": "subfail001",
            "answer_text": "Answer kept",
            "submitted_at": datetime.now(timezone.utc),
            "evaluation_status": "failed",
            "evaluation": None,
            "evaluated_at": None,
            "evaluation_error": "temporary",
        }
    ]
    interview_repo.update_answer_evaluation = AsyncMock(return_value=failed)

    response = client.post(
        f"/api/v1/interviews/{session_id}/answers",
        headers=headers,
        json={"submission_id": "subfail001", "answer_text": "Answer kept"},
    )
    assert response.status_code == 200
    answer = response.json()["answers"][0]
    assert answer["answer_text"] == "Answer kept"
    assert answer["evaluation_status"] == "failed"


def test_get_session_wrong_user(interview_client):
    client, interview_repo, headers, _user_id = interview_client
    interview_repo.find_by_id_for_user = AsyncMock(return_value=None)

    response = client.get(
        "/api/v1/interviews/507f1f77bcf86cd799439020",
        headers=headers,
    )
    assert response.status_code == 404


@patch("services.interview_service.evaluate_answer_text")
def test_complete_interview_allows_skipped_follow_up(mock_evaluate, interview_client):
    client, interview_repo, headers, user_id = interview_client
    doc = _session_doc(user_id)
    session_id = str(doc["_id"])
    doc["questions"][1] = {
        **doc["questions"][1],
        "id": "fu1",
        "is_follow_up": True,
        "parent_question_id": "q1",
        "follow_up_type": "clarification",
        "skipped": True,
    }
    evaluation = sample_evaluation().model_dump()
    doc["answers"] = [
        {
            "question_id": "q1",
            "submission_id": "subcomplete01",
            "answer_text": "answer",
            "submitted_at": datetime.now(timezone.utc),
            "evaluation_status": "evaluated",
            "evaluation": evaluation,
            "evaluated_at": datetime.now(timezone.utc),
            "evaluation_error": None,
        },
        {
            "question_id": "q3",
            "submission_id": "subcomplete03",
            "answer_text": "answer",
            "submitted_at": datetime.now(timezone.utc),
            "evaluation_status": "evaluated",
            "evaluation": evaluation,
            "evaluated_at": datetime.now(timezone.utc),
            "evaluation_error": None,
        },
    ]
    doc["current_question_index"] = 3
    interview_repo.find_by_id_for_user = AsyncMock(return_value=doc)
    completed = {**doc, "status": "completed", "summary": {
        "total_questions": 3,
        "answered_questions": 2,
        "average_score": 80.0,
        "highlights": [],
        "focus_areas": [],
    }}
    interview_repo.complete_session = AsyncMock(return_value=completed)

    response = client.post(
        f"/api/v1/interviews/{session_id}/complete",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


@patch("services.interview_service.evaluate_answer_text")
def test_complete_interview(mock_evaluate, interview_client):
    client, interview_repo, headers, user_id = interview_client
    doc = _session_doc(user_id)
    session_id = str(doc["_id"])
    evaluation = sample_evaluation().model_dump()
    doc["answers"] = [
        {
            "question_id": f"q{i}",
            "submission_id": f"subcomplete{i:02d}",
            "answer_text": "answer",
            "submitted_at": datetime.now(timezone.utc),
            "evaluation_status": "evaluated",
            "evaluation": evaluation,
            "evaluated_at": datetime.now(timezone.utc),
            "evaluation_error": None,
        }
        for i in range(1, 4)
    ]
    doc["current_question_index"] = 3
    interview_repo.find_by_id_for_user = AsyncMock(return_value=doc)

    completed = {**doc, "status": "completed", "summary": {
        "total_questions": 3,
        "answered_questions": 3,
        "average_score": 80.0,
        "highlights": [],
        "focus_areas": [],
    }}
    interview_repo.complete_session = AsyncMock(return_value=completed)

    response = client.post(
        f"/api/v1/interviews/{session_id}/complete",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["summary"]["average_score"] == 80.0


@patch("services.follow_up_service.generate_follow_up_question")
@patch("services.interview_service.evaluate_answer_text")
def test_submit_answer_inserts_follow_up(mock_evaluate, mock_follow_up, interview_client):
    client, interview_repo, headers, user_id = interview_client
    doc = _session_doc(user_id)
    doc["base_question_count"] = 3
    session_id = str(doc["_id"])
    interview_repo.find_by_id_for_user = AsyncMock(return_value=doc)
    mock_evaluate.return_value = sample_evaluation(score=2)
    mock_follow_up.return_value = GeminiFollowUpQuestionPayload(
        should_ask_follow_up=True,
        follow_up_type="clarification",
        question="Which specific pattern did you apply in production?",
        category="technical",
        difficulty="intermediate",
    )

    after_eval = {**doc, "current_question_index": 0}
    after_eval["answers"] = [
        {
            "question_id": "q1",
            "submission_id": "subfollow001",
            "answer_text": "Short answer",
            "submitted_at": datetime.now(timezone.utc),
            "evaluation_status": "evaluated",
            "evaluation": sample_evaluation(score=2).model_dump(),
            "evaluated_at": datetime.now(timezone.utc),
            "evaluation_error": None,
        }
    ]
    follow_up_item = {
        "id": "fu1",
        "question": "Which specific pattern did you apply in production?",
        "category": "technical",
        "difficulty": "intermediate",
        "relevance": "Python",
        "evaluates": "Depth",
        "is_follow_up": True,
        "parent_question_id": "q1",
        "follow_up_type": "clarification",
        "skipped": False,
    }
    with_follow_up = {**after_eval}
    with_follow_up["questions"] = [
        doc["questions"][0],
        follow_up_item,
        *doc["questions"][1:],
    ]
    with_follow_up["current_question_index"] = 1

    interview_repo.append_answer_pending = AsyncMock(return_value=doc)
    interview_repo.update_answer_evaluation = AsyncMock(return_value=after_eval)
    interview_repo.insert_follow_up_question = AsyncMock(return_value=with_follow_up)
    interview_repo.advance_question_index = AsyncMock()

    response = client.post(
        f"/api/v1/interviews/{session_id}/answers",
        headers=headers,
        json={"submission_id": "subfollow001", "answer_text": "Short answer"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_question_index"] == 1
    assert body["questions"][1]["is_follow_up"] is True
    interview_repo.insert_follow_up_question.assert_awaited_once()
    interview_repo.advance_question_index.assert_not_awaited()


def test_skip_follow_up_endpoint(interview_client):
    client, interview_repo, headers, user_id = interview_client
    doc = _session_doc(user_id)
    doc["questions"][1] = {
        "id": "fu1",
        "question": "Follow-up?",
        "category": "technical",
        "difficulty": "intermediate",
        "relevance": "Python",
        "evaluates": "Depth",
        "is_follow_up": True,
        "parent_question_id": "q1",
        "follow_up_type": "clarification",
        "skipped": False,
    }
    doc["current_question_index"] = 1
    session_id = str(doc["_id"])
    skipped = {**doc, "current_question_index": 2}
    skipped["questions"][1] = {**skipped["questions"][1], "skipped": True}

    interview_repo.find_by_id_for_user = AsyncMock(return_value=doc)
    interview_repo.skip_follow_up_question = AsyncMock(return_value=skipped)

    response = client.post(
        f"/api/v1/interviews/{session_id}/questions/fu1/skip",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["current_question_index"] == 2


def test_completed_session_submit_rejected(interview_client):
    client, interview_repo, headers, user_id = interview_client
    doc = _session_doc(user_id)
    doc["status"] = "completed"
    interview_repo.find_by_id_for_user = AsyncMock(return_value=doc)

    response = client.post(
        f"/api/v1/interviews/{doc['_id']}/answers",
        headers=headers,
        json={"submission_id": "subcomplet", "answer_text": "too late"},
    )
    assert response.status_code == 409
