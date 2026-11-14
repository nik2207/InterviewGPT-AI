from unittest.mock import AsyncMock, patch
import pytest
from bson import ObjectId

from schemas.interview_schema import GeminiFollowUpQuestionPayload
from services.follow_up_service import (
    build_follow_up_question,
    count_follow_ups,
    follow_up_cap,
    has_follow_up_for_parent,
    maybe_insert_follow_up,
    skip_follow_up_question,
)


def test_follow_up_cap_from_base_count():
    session = {"base_question_count": 8, "questions": [{}] * 8}
    assert follow_up_cap(session) == 4


def test_has_follow_up_for_parent_detects_child():
    parent = "parent1"
    questions = [
        {"id": parent, "is_follow_up": False},
        {
            "id": "child",
            "is_follow_up": True,
            "parent_question_id": parent,
        },
    ]
    assert has_follow_up_for_parent(questions, parent)
    assert not has_follow_up_for_parent(questions, "other")


def test_build_follow_up_question_validates_length():
    parent = {"id": "p1", "category": "tech", "difficulty": "intermediate"}
    payload = GeminiFollowUpQuestionPayload(
        should_ask_follow_up=True,
        follow_up_type="clarification",
        question="Hi",
    )
    assert build_follow_up_question(parent, payload) is None

    payload2 = GeminiFollowUpQuestionPayload(
        should_ask_follow_up=True,
        follow_up_type="technical_depth",
        question="Can you walk through the error handling path?",
    )
    built = build_follow_up_question(parent, payload2)
    assert built is not None
    assert built["is_follow_up"] is True
    assert built["parent_question_id"] == "p1"


@pytest.mark.asyncio
@patch("services.follow_up_service.generate_follow_up_question")
async def test_maybe_insert_follow_up_prevents_duplicate(mock_generate):
    parent_id = "q-parent"
    parent = {
        "id": parent_id,
        "question": "Explain caching?",
        "category": "technical",
        "difficulty": "intermediate",
        "is_follow_up": False,
    }
    session = {
        "role": "Engineer",
        "interview_type": "technical",
        "base_question_count": 3,
        "current_question_index": 0,
        "questions": [
            parent,
            {
                "id": "existing-fu",
                "is_follow_up": True,
                "parent_question_id": parent_id,
            },
        ],
    }
    repo = AsyncMock()
    result = await maybe_insert_follow_up(
        session=session,
        parent_question=parent,
        answer_text="vague answer",
        evaluation={
            "dimension_scores": {"completeness": 2, "relevance": 3},
            "missing_concepts": ["TTL"],
            "overall_score": 50,
        },
        interview_repo=repo,
        session_id="abc",
        user_id="user1",
    )
    assert result is None
    mock_generate.assert_not_called()
    repo.insert_follow_up_question.assert_not_called()


@pytest.mark.asyncio
@patch("services.follow_up_service.generate_follow_up_question")
async def test_maybe_insert_follow_up_inserts_once(mock_generate):
    parent_id = "q-parent"
    parent = {
        "id": parent_id,
        "question": "Explain caching?",
        "category": "technical",
        "difficulty": "intermediate",
        "is_follow_up": False,
    }
    session = {
        "role": "Engineer",
        "interview_type": "technical",
        "base_question_count": 3,
        "current_question_index": 0,
        "questions": [parent],
    }
    mock_generate.return_value = GeminiFollowUpQuestionPayload(
        should_ask_follow_up=True,
        follow_up_type="clarification",
        question="Which cache invalidation strategy did you use?",
        category="technical",
        difficulty="intermediate",
    )
    updated = {**session, "questions": [parent, {"id": "fu1", "is_follow_up": True}]}
    repo = AsyncMock()
    repo.insert_follow_up_question = AsyncMock(return_value=updated)

    result = await maybe_insert_follow_up(
        session=session,
        parent_question=parent,
        answer_text="We used Redis.",
        evaluation={
            "dimension_scores": {"completeness": 2, "relevance": 3},
            "missing_concepts": ["invalidation"],
            "overall_score": 55,
        },
        interview_repo=repo,
        session_id="abc",
        user_id="user1",
    )
    assert result == updated
    repo.insert_follow_up_question.assert_awaited_once()
    assert count_follow_ups(updated["questions"]) == 1


@pytest.mark.asyncio
async def test_skip_follow_up_question_advances_index():
    question_id = "fu-q1"
    session = {
        "_id": ObjectId(),
        "user_id": "user1",
        "status": "in_progress",
        "current_question_index": 1,
        "questions": [
            {"id": "q1", "is_follow_up": False},
            {
                "id": question_id,
                "is_follow_up": True,
                "parent_question_id": "q1",
                "skipped": False,
            },
            {"id": "q2", "is_follow_up": False},
        ],
    }
    updated = {
        **session,
        "current_question_index": 2,
        "questions": [
            session["questions"][0],
            {**session["questions"][1], "skipped": True},
            session["questions"][2],
        ],
    }
    repo = AsyncMock()
    repo.find_by_id_for_user = AsyncMock(return_value=session)
    repo.skip_follow_up_question = AsyncMock(return_value=updated)

    result = await skip_follow_up_question(
        "user1", str(session["_id"]), question_id, repo
    )
    assert result["current_question_index"] == 2
    assert result["questions"][1]["skipped"] is True


@pytest.mark.asyncio
async def test_skip_follow_up_wrong_user_session_not_found():
    repo = AsyncMock()
    repo.find_by_id_for_user = AsyncMock(return_value=None)
    from services.follow_up_service import FollowUpServiceError

    with pytest.raises(FollowUpServiceError) as exc:
        await skip_follow_up_question("user1", str(ObjectId()), "q", repo)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
@patch("services.follow_up_service.generate_follow_up_question")
async def test_maybe_insert_follow_up_skips_strong_answer(mock_generate):
    parent = {
        "id": "p1",
        "question": "Explain CI/CD?",
        "category": "technical",
        "difficulty": "intermediate",
        "is_follow_up": False,
    }
    session = {
        "role": "Engineer",
        "interview_type": "technical",
        "base_question_count": 4,
        "questions": [parent],
    }
    repo = AsyncMock()
    result = await maybe_insert_follow_up(
        session=session,
        parent_question=parent,
        answer_text="Detailed pipeline with stages and rollback.",
        evaluation={
            "dimension_scores": {"completeness": 5, "relevance": 5},
            "missing_concepts": [],
            "overall_score": 92,
        },
        interview_repo=repo,
        session_id="abc",
        user_id="user1",
    )
    assert result is None
    mock_generate.assert_not_called()


@pytest.mark.asyncio
@patch("services.follow_up_service.generate_follow_up_question")
async def test_maybe_insert_follow_up_respects_cap(mock_generate):
    parent_id = "parent-new"
    parent = {
        "id": parent_id,
        "question": "New parent?",
        "category": "technical",
        "difficulty": "intermediate",
        "is_follow_up": False,
    }
    existing_follow_ups = [
        {
            "id": f"fu{i}",
            "is_follow_up": True,
            "parent_question_id": f"p{i}",
        }
        for i in range(2)
    ]
    session = {
        "role": "Engineer",
        "interview_type": "technical",
        "base_question_count": 4,
        "questions": [parent, *existing_follow_ups],
    }
    repo = AsyncMock()
    result = await maybe_insert_follow_up(
        session=session,
        parent_question=parent,
        answer_text="vague",
        evaluation={
            "dimension_scores": {"completeness": 2, "relevance": 2},
            "missing_concepts": ["detail"],
            "overall_score": 40,
        },
        interview_repo=repo,
        session_id="abc",
        user_id="user1",
    )
    assert result is None
    mock_generate.assert_not_called()


@pytest.mark.asyncio
@patch("services.follow_up_service.generate_follow_up_question")
async def test_maybe_insert_follow_up_gemini_failure_silent(mock_generate):
    from services.gemini_follow_up_service import FollowUpGenerationError

    parent = {
        "id": "p1",
        "question": "Explain caching?",
        "category": "technical",
        "difficulty": "intermediate",
        "is_follow_up": False,
    }
    session = {
        "role": "Engineer",
        "interview_type": "technical",
        "base_question_count": 3,
        "questions": [parent],
    }
    mock_generate.side_effect = FollowUpGenerationError("bad json")
    repo = AsyncMock()
    result = await maybe_insert_follow_up(
        session=session,
        parent_question=parent,
        answer_text="short",
        evaluation={
            "dimension_scores": {"completeness": 2, "relevance": 2},
            "missing_concepts": ["TTL"],
            "overall_score": 50,
        },
        interview_repo=repo,
        session_id="abc",
        user_id="user1",
    )
    assert result is None
    repo.insert_follow_up_question.assert_not_called()
