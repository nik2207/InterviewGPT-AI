from uuid import uuid4
import asyncio

from core.config.settings import settings
from repositories.interview_repository import InterviewRepository, InterviewRepositoryError
from schemas.interview_schema import GeminiFollowUpQuestionPayload
from services.interview_language_service import resolve_language_settings
from services.gemini_follow_up_service import (
    FollowUpGenerationError,
    generate_follow_up_question,
)


class FollowUpServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def follow_up_cap(session: dict) -> int:
    base = int(session.get("base_question_count") or len(session.get("questions", [])))
    return min(5, max(1, base // 2))


def count_follow_ups(questions: list[dict]) -> int:
    return sum(1 for q in questions if q.get("is_follow_up"))


def has_follow_up_for_parent(questions: list[dict], parent_id: str) -> bool:
    return any(
        q.get("parent_question_id") == parent_id and q.get("is_follow_up")
        for q in questions
    )


def _heuristic_needs_follow_up(evaluation: dict) -> bool:
    dims = evaluation.get("dimension_scores") or {}
    completeness = dims.get("completeness", 5)
    relevance = dims.get("relevance", 5)
    if completeness <= 3 or relevance <= 3:
        return True
    if evaluation.get("missing_concepts"):
        return True
    coach = evaluation.get("improvement_coach") or {}
    if coach.get("missing_important_points"):
        return True
    return evaluation.get("overall_score", 100) < 75


def build_follow_up_question(
    parent: dict,
    payload: GeminiFollowUpQuestionPayload,
) -> dict | None:
    if not payload.should_ask_follow_up or not payload.question:
        return None
    follow_type = payload.follow_up_type
    if follow_type is None:
        return None

    text = payload.question.strip()
    if len(text) < 5:
        return None

    return {
        "id": uuid4().hex,
        "question": text,
        "category": payload.category or parent.get("category", "general"),
        "difficulty": payload.difficulty or parent.get("difficulty", "intermediate"),
        "relevance": payload.relevance or parent.get("relevance", "Follow-up"),
        "evaluates": payload.evaluates or parent.get("evaluates", "Depth"),
        "is_follow_up": True,
        "parent_question_id": parent["id"],
        "follow_up_type": follow_type,
        "skipped": False,
    }


async def maybe_insert_follow_up(
    *,
    session: dict,
    parent_question: dict,
    answer_text: str,
    evaluation: dict,
    interview_repo: InterviewRepository,
    session_id: str,
    user_id: str,
) -> dict | None:
    if parent_question.get("is_follow_up"):
        return None

    questions = session.get("questions", [])
    if has_follow_up_for_parent(questions, parent_question["id"]):
        return None

    if len(questions) >= settings.INTERVIEW_MAX_QUESTIONS:
        return None

    if count_follow_ups(questions) >= follow_up_cap(session):
        return None

    if not _heuristic_needs_follow_up(evaluation):
        return None

    existing_text = [q.get("question", "") for q in questions]
    try:
        gemini = await asyncio.to_thread(
            generate_follow_up_question,
            role=session.get("role", "Interview"),
            interview_type=session.get("interview_type", "mixed"),
            parent_question=parent_question,
            answer_text=answer_text,
            evaluation=evaluation,
            existing_questions=existing_text,
            language_settings=resolve_language_settings(session),
        )
    except FollowUpGenerationError:
        return None

    new_question = build_follow_up_question(parent_question, gemini)
    if new_question is None:
        return None

    current_index = int(session.get("current_question_index", 0))
    try:
        return await interview_repo.insert_follow_up_question(
            session_id=session_id,
            user_id=user_id,
            current_index=current_index,
            question=new_question,
            parent_question_id=parent_question["id"],
        )
    except InterviewRepositoryError:
        return None


async def skip_follow_up_question(
    user_id: str,
    session_id: str,
    question_id: str,
    interview_repo: InterviewRepository,
) -> dict:
    document = await interview_repo.find_by_id_for_user(session_id, user_id)
    if document is None:
        raise FollowUpServiceError("Interview session not found", status_code=404)

    index = int(document.get("current_question_index", 0))
    questions = document.get("questions", [])
    if index >= len(questions):
        raise FollowUpServiceError("No active question.", status_code=409)

    current = questions[index]
    if current.get("id") != question_id:
        raise FollowUpServiceError(
            "Can only skip the current follow-up question.", status_code=422
        )
    if not current.get("is_follow_up"):
        raise FollowUpServiceError(
            "Only follow-up questions can be skipped.", status_code=422
        )

    try:
        updated = await interview_repo.skip_follow_up_question(
            session_id, user_id, question_id
        )
    except InterviewRepositoryError as exc:
        raise FollowUpServiceError(str(exc), status_code=500) from exc

    if updated is None:
        raise FollowUpServiceError("Unable to skip question.", status_code=409)

    return updated
