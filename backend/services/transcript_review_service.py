from schemas.interview_schema import (
    InterviewAnswerRecord,
    InterviewQuestionSnapshot,
    InterviewTranscriptReviewResponse,
    PracticeRevisionSnapshot,
    TranscriptReviewItem,
    TranscriptTiming,
    VoiceTranscriptEntry,
)
from services.interview_language_service import resolve_language_settings

WEAK_SCORE_THRESHOLD = 70


def _practice_map(document: dict) -> dict[str, dict]:
    revisions = document.get("practice_revisions") or []
    return {item["question_id"]: item for item in revisions if item.get("question_id")}


def _is_weak_answer(answer: dict | None) -> bool:
    if answer is None:
        return False
    evaluation = answer.get("evaluation")
    if not evaluation:
        return answer.get("evaluation_status") == "failed"
    score = evaluation.get("overall_score", 100)
    if score < WEAK_SCORE_THRESHOLD:
        return True
    dims = evaluation.get("dimension_scores") or {}
    if dims.get("completeness", 5) <= 2 or dims.get("relevance", 5) <= 2:
        return True
    return bool(evaluation.get("missing_concepts"))


def _timing_from_answer(answer: dict | None) -> TranscriptTiming | None:
    if answer is None:
        return None
    submitted_at = answer.get("submitted_at")
    metrics = answer.get("speech_metrics") or {}
    reliable = bool(metrics.get("speech_timing_available"))
    duration = metrics.get("duration_seconds")
    wpm = metrics.get("words_per_minute")
    if submitted_at is None and not reliable:
        return None
    return TranscriptTiming(
        submitted_at=submitted_at,
        duration_seconds=duration if reliable else None,
        words_per_minute=wpm if reliable else None,
        timing_reliable=reliable and duration is not None,
    )


def _voice_for_question(document: dict, question_id: str) -> list[VoiceTranscriptEntry]:
    voice = document.get("voice_interview") or {}
    items = []
    for raw in voice.get("transcript") or []:
        if raw.get("question_id") != question_id:
            continue
        items.append(VoiceTranscriptEntry.model_validate(raw))
    return items


def _answer_status(question: dict, answer: dict | None) -> str:
    if question.get("skipped"):
        return "skipped"
    if answer is None:
        return "unanswered"
    status = answer.get("evaluation_status", "pending")
    if status == "evaluated":
        return "answered"
    return status


def build_transcript_review(
    document: dict,
    *,
    session_id: str,
) -> InterviewTranscriptReviewResponse:
    bookmarks = list(document.get("review_bookmarks") or [])
    bookmark_set = set(bookmarks)
    practice = _practice_map(document)
    items: list[TranscriptReviewItem] = []

    for index, raw_question in enumerate(document.get("questions") or [], start=1):
        question = InterviewQuestionSnapshot.model_validate(raw_question)
        answer_raw = _find_answer(document, question.id)

        answer_model = (
            InterviewAnswerRecord.model_validate(answer_raw) if answer_raw else None
        )
        status = _answer_status(raw_question, answer_raw)
        practice_raw = practice.get(question.id)
        practice_model = (
            PracticeRevisionSnapshot.model_validate(practice_raw)
            if practice_raw
            else None
        )

        items.append(
            TranscriptReviewItem(
                sequence=index,
                question=question,
                answer=answer_model,
                answer_status=status,
                is_weak=_is_weak_answer(answer_raw),
                is_bookmarked=question.id in bookmark_set,
                timing=_timing_from_answer(answer_raw),
                voice_transcript=_voice_for_question(document, question.id),
                audio_recording_available=False,
                practice_revision=practice_model,
            )
        )

    lang = resolve_language_settings(document)
    return InterviewTranscriptReviewResponse(
        session_id=session_id,
        role=document.get("role", "Interview"),
        status=document.get("status", "in_progress"),
        completed_at=document.get("completed_at"),
        bookmarks=bookmarks,
        items=items,
        audio_playback_supported=False,
        language_settings=lang,
    )


def _find_answer(document: dict, question_id: str) -> dict | None:
    for item in reversed(document.get("answers") or []):
        if item.get("question_id") == question_id:
            return item
    return None
