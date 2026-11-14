from datetime import datetime, timezone
from uuid import uuid4

from bson import ObjectId

from core.config.settings import settings
from repositories.analysis_repository import AnalysisRepository
from repositories.billing_repository import BillingRepository
from repositories.interview_repository import InterviewRepository, InterviewRepositoryError
from repositories.resume_repository import ResumeRepository
from schemas.interview_schema import (
    AnswerEvaluationResponse,
    CreateInterviewSessionRequest,
    InterviewAnswerRecord,
    InterviewHistoryItem,
    InterviewHistoryListResponse,
    InterviewQuestionSnapshot,
    InterviewSessionListResponse,
    InterviewSessionResponse,
    InterviewSessionSummary,
    InterviewTranscriptReviewResponse,
    SpeechMetricsRecord,
    SubmitAnswerRequest,
    UpdatePracticeRevisionRequest,
    UpdateTranscriptBookmarksRequest,
    VoiceInterviewState,
)
from services.follow_up_service import (
    FollowUpServiceError,
    follow_up_cap,
    maybe_insert_follow_up,
    skip_follow_up_question,
)
from services.voice_interview_service import build_voice_state
from services.interview_report_pdf import generate_interview_report_pdf
from services.interview_transcript_pdf import generate_interview_transcript_pdf
from services.transcript_review_service import build_transcript_review
from services.speech_metrics_service import build_speech_metrics
from services.gemini_answer_evaluation_service import (
    AnswerEvaluationError,
    AnswerEvaluationUnavailableError,
    evaluate_answer_text,
)
from services.gemini_interview_localization_service import (
    QuestionLocalizationError,
    localize_interview_questions,
)
from services.entitlement_service import (
    effective_plan_id,
    redact_coaching_if_needed,
)
from services.interview_language_service import (
    language_settings_to_document,
    resolve_language_settings,
)


class InterviewServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _oid_str(value) -> str:
    if isinstance(value, ObjectId):
        return str(value)
    return str(value)


def _session_to_response(document: dict) -> InterviewSessionResponse:
    answers = [
        InterviewAnswerRecord.model_validate(item) for item in document.get("answers", [])
    ]
    questions = [
        InterviewQuestionSnapshot.model_validate(item)
        for item in document.get("questions", [])
    ]
    summary = document.get("summary")
    return InterviewSessionResponse(
        id=_oid_str(document["_id"]),
        user_id=document["user_id"],
        role=document["role"],
        difficulty=document["difficulty"],
        interview_type=document["interview_type"],
        resume_id=document.get("resume_id"),
        status=document["status"],
        questions=questions,
        base_question_count=document.get("base_question_count"),
        follow_up_cap=follow_up_cap(document),
        current_question_index=document["current_question_index"],
        answers=answers,
        summary=InterviewSessionSummary.model_validate(summary) if summary else None,
        created_at=document["created_at"],
        updated_at=document["updated_at"],
        completed_at=document.get("completed_at"),
        voice_interview=(
            VoiceInterviewState.model_validate(document["voice_interview"])
            if document.get("voice_interview")
            else None
        ),
        language_settings=resolve_language_settings(document),
    )


def _build_questions_from_analysis(
    analysis_doc: dict,
    difficulty: str,
    count: int,
) -> list[dict]:
    raw_questions = analysis_doc.get("interview_questions", [])
    selected = []
    for item in raw_questions:
        if item.get("difficulty") == difficulty:
            selected.append(item)
    pool = selected if selected else list(raw_questions)
    pool = pool[:count]
    snapshots = []
    for item in pool:
        snapshots.append(
            {
                "id": uuid4().hex,
                "question": item["question"],
                "category": item.get("category", "general"),
                "difficulty": item.get("difficulty", difficulty),
                "relevance": item.get("relevance", "Resume"),
                "evaluates": item.get("evaluates", "Role fit"),
            }
        )
    return snapshots


async def create_interview_session(
    user_id: str,
    payload: CreateInterviewSessionRequest,
    interview_repo: InterviewRepository,
    resume_repo: ResumeRepository,
    analysis_repo: AnalysisRepository,
) -> InterviewSessionResponse:
    questions: list[dict] = []

    if payload.custom_questions:
        questions = [
            {
                "id": uuid4().hex,
                "question": item.question,
                "category": item.category,
                "difficulty": item.difficulty,
                "relevance": item.relevance,
                "evaluates": item.evaluates,
            }
            for item in payload.custom_questions[: settings.INTERVIEW_MAX_QUESTIONS]
        ]
        resume_id = payload.resume_id
    elif payload.resume_id:
        resume = await resume_repo.find_by_id_for_user(payload.resume_id, user_id)
        if resume is None:
            raise InterviewServiceError("Resume not found", status_code=404)
        analysis = await analysis_repo.find_latest_for_resume(user_id, payload.resume_id)
        if analysis is None:
            raise InterviewServiceError(
                "No saved resume analysis found. Analyze the resume first.",
                status_code=422,
            )
        questions = _build_questions_from_analysis(
            analysis,
            payload.difficulty,
            min(payload.question_count, settings.INTERVIEW_MAX_QUESTIONS),
        )
        resume_id = payload.resume_id
    else:
        raise InterviewServiceError(
            "Provide resume_id with saved analysis or custom_questions.",
            status_code=422,
        )

    if len(questions) < settings.INTERVIEW_MIN_QUESTIONS:
        raise InterviewServiceError(
            f"At least {settings.INTERVIEW_MIN_QUESTIONS} questions are required.",
            status_code=422,
        )

    language_settings = payload.language
    if language_settings.practice_professional_english:
        language_settings = language_settings.model_copy(
            update={"feedback_language": "en"}
        )
    if language_settings.question_language != "en":
        try:
            questions = localize_interview_questions(
                questions, language_settings.question_language
            )
        except QuestionLocalizationError:
            pass

    document = {
        "user_id": user_id,
        "role": payload.role.strip(),
        "difficulty": payload.difficulty,
        "interview_type": payload.interview_type,
        "resume_id": resume_id,
        "status": "in_progress",
        "questions": questions,
        "base_question_count": len(questions),
        "current_question_index": 0,
        "answers": [],
        "review_bookmarks": [],
        "practice_revisions": [],
        "summary": None,
        "completed_at": None,
        "voice_interview": build_voice_state(
            payload.voice_interview_enabled,
            payload.interviewer_tone,
        ),
        "language_settings": language_settings_to_document(language_settings),
    }

    try:
        saved = await interview_repo.create_session(document)
    except InterviewRepositoryError:
        raise InterviewServiceError(
            "Unable to create interview session.", status_code=500
        ) from None

    return _session_to_response(saved)


async def get_interview_session(
    user_id: str,
    session_id: str,
    interview_repo: InterviewRepository,
) -> InterviewSessionResponse:
    document = await interview_repo.find_by_id_for_user(session_id, user_id)
    if document is None:
        raise InterviewServiceError("Interview session not found", status_code=404)
    return _session_to_response(document)


async def list_interview_sessions(
    user_id: str,
    interview_repo: InterviewRepository,
) -> InterviewSessionListResponse:
    documents = await interview_repo.list_by_user(user_id)
    return InterviewSessionListResponse(
        sessions=[_session_to_response(doc) for doc in documents]
    )


async def list_interview_history(
    user_id: str,
    interview_repo: InterviewRepository,
) -> InterviewHistoryListResponse:
    try:
        documents = await interview_repo.list_completed_by_user(user_id)
    except InterviewRepositoryError:
        raise InterviewServiceError(
            "Unable to load interview history.", status_code=500
        ) from None

    items: list[InterviewHistoryItem] = []
    for document in documents:
        summary = document.get("summary") or {}
        completed_at = document.get("completed_at") or document.get("updated_at")
        items.append(
            InterviewHistoryItem(
                id=_oid_str(document["_id"]),
                role=document.get("role", "Interview"),
                difficulty=document.get("difficulty", "intermediate"),
                interview_type=document.get("interview_type", "mixed"),
                completed_at=completed_at,
                question_count=int(
                    summary.get("total_questions", len(document.get("questions", [])))
                ),
                overall_score=summary.get("average_score"),
            )
        )
    return InterviewHistoryListResponse(interviews=items)


async def get_interview_report_pdf(
    user_id: str,
    session_id: str,
    interview_repo: InterviewRepository,
) -> tuple[bytes, str]:
    document = await interview_repo.find_by_id_for_user(session_id, user_id)
    if document is None:
        raise InterviewServiceError("Interview session not found", status_code=404)
    if document.get("status") != "completed":
        raise InterviewServiceError(
            "Report is available only for completed interviews.",
            status_code=422,
        )
    if not document.get("summary"):
        raise InterviewServiceError(
            "Interview summary is not available for this session.",
            status_code=422,
        )

    pdf_bytes = generate_interview_report_pdf(document)
    if not pdf_bytes:
        raise InterviewServiceError("Failed to generate report.", status_code=500)

    safe_id = _oid_str(document["_id"])[:12]
    filename = f"interview-report-{safe_id}.pdf"
    return pdf_bytes, filename


async def get_interview_transcript_review(
    user_id: str,
    session_id: str,
    interview_repo: InterviewRepository,
) -> InterviewTranscriptReviewResponse:
    document = await interview_repo.find_by_id_for_user(session_id, user_id)
    if document is None:
        raise InterviewServiceError("Interview session not found", status_code=404)
    return build_transcript_review(document, session_id=_oid_str(document["_id"]))


async def update_transcript_bookmarks(
    user_id: str,
    session_id: str,
    payload: UpdateTranscriptBookmarksRequest,
    interview_repo: InterviewRepository,
) -> InterviewTranscriptReviewResponse:
    document = await interview_repo.find_by_id_for_user(session_id, user_id)
    if document is None:
        raise InterviewServiceError("Interview session not found", status_code=404)
    try:
        updated = await interview_repo.set_review_bookmarks(
            session_id, user_id, payload.question_ids
        )
    except InterviewRepositoryError:
        raise InterviewServiceError("Unable to update bookmarks.", status_code=500) from None
    if updated is None:
        raise InterviewServiceError("Interview session not found", status_code=404)
    return build_transcript_review(updated, session_id=session_id)


async def save_practice_revision(
    user_id: str,
    session_id: str,
    question_id: str,
    payload: UpdatePracticeRevisionRequest,
    interview_repo: InterviewRepository,
) -> InterviewTranscriptReviewResponse:
    draft = payload.draft_text.strip()
    if not draft:
        raise InterviewServiceError("Practice draft cannot be empty.", status_code=422)
    if len(draft) > settings.INTERVIEW_MAX_ANSWER_CHARS:
        raise InterviewServiceError(
            f"Draft exceeds {settings.INTERVIEW_MAX_ANSWER_CHARS} characters.",
            status_code=422,
        )
    document = await interview_repo.find_by_id_for_user(session_id, user_id)
    if document is None:
        raise InterviewServiceError("Interview session not found", status_code=404)
    try:
        updated = await interview_repo.upsert_practice_revision(
            session_id, user_id, question_id, draft
        )
    except InterviewRepositoryError:
        raise InterviewServiceError("Unable to save practice draft.", status_code=500) from None
    if updated is None:
        raise InterviewServiceError("Question not found in this session.", status_code=404)
    return build_transcript_review(updated, session_id=session_id)


async def get_interview_transcript_pdf(
    user_id: str,
    session_id: str,
    interview_repo: InterviewRepository,
) -> tuple[bytes, str]:
    document = await interview_repo.find_by_id_for_user(session_id, user_id)
    if document is None:
        raise InterviewServiceError("Interview session not found", status_code=404)
    if not document.get("answers"):
        raise InterviewServiceError(
            "Transcript export requires at least one saved answer.",
            status_code=422,
        )
    pdf_bytes = generate_interview_transcript_pdf(
        document, session_id=_oid_str(document["_id"])
    )
    if not pdf_bytes:
        raise InterviewServiceError("Failed to generate transcript.", status_code=500)
    safe_id = _oid_str(document["_id"])[:12]
    return pdf_bytes, f"interview-transcript-{safe_id}.pdf"


async def delete_interview_session(
    user_id: str,
    session_id: str,
    interview_repo: InterviewRepository,
) -> None:
    try:
        deleted = await interview_repo.delete_session_for_user(session_id, user_id)
    except InterviewRepositoryError:
        raise InterviewServiceError("Unable to delete interview.", status_code=500) from None
    if not deleted:
        raise InterviewServiceError("Interview session not found", status_code=404)


def _current_question(document: dict) -> dict | None:
    index = int(document.get("current_question_index", 0))
    questions = document.get("questions", [])
    if index >= len(questions):
        return None
    return questions[index]


def _evaluation_to_dict(evaluation: AnswerEvaluationResponse) -> dict:
    return evaluation.model_dump()


async def submit_answer(
    user_id: str,
    session_id: str,
    payload: SubmitAnswerRequest,
    interview_repo: InterviewRepository,
    billing_repo: BillingRepository | None = None,
) -> InterviewSessionResponse:
    document = await interview_repo.find_by_id_for_user(session_id, user_id)
    if document is None:
        raise InterviewServiceError("Interview session not found", status_code=404)
    if document.get("status") != "in_progress":
        raise InterviewServiceError(
            "Interview session is already completed.", status_code=409
        )

    question = _current_question(document)
    if question is None:
        raise InterviewServiceError(
            "All questions have been answered. Complete the interview.",
            status_code=409,
        )

    question_id = question["id"]
    submission_id = payload.submission_id.strip()
    answer_text = payload.answer_text.strip()

    existing = interview_repo.find_answer_by_submission(
        document, question_id, submission_id
    )
    if existing is not None:
        return _session_to_response(document)

    latest = interview_repo.find_answer_for_question(document, question_id)
    if latest is not None and latest.get("evaluation_status") == "evaluated":
        raise InterviewServiceError(
            "This question has already been answered.", status_code=409
        )

    if payload.retry_evaluation:
        document = await interview_repo.find_by_id_for_user(session_id, user_id)
        if document is None:
            raise InterviewServiceError("Interview session not found", status_code=404)
        question = _current_question(document)
        if question is None:
            raise InterviewServiceError(
                "All questions have been answered. Complete the interview.",
                status_code=409,
            )
        question_id = question["id"]
        latest = interview_repo.find_answer_for_question(document, question_id)
        if latest is None or latest.get("evaluation_status") != "failed":
            raise InterviewServiceError(
                "No failed evaluation to retry for the current question.",
                status_code=400,
            )
        answer_text = (latest.get("answer_text") or "").strip()
        submission_id = latest.get("submission_id", submission_id)
    else:
        if not answer_text:
            raise InterviewServiceError("Answer cannot be empty.", status_code=422)
        if len(answer_text) > settings.INTERVIEW_MAX_ANSWER_CHARS:
            raise InterviewServiceError(
                f"Answer exceeds {settings.INTERVIEW_MAX_ANSWER_CHARS} characters.",
                status_code=422,
            )

        input_mode = "typed"
        duration_seconds = None
        if payload.speech_metrics is not None:
            input_mode = payload.speech_metrics.input_mode
            duration_seconds = payload.speech_metrics.duration_seconds

        speech_dict = build_speech_metrics(
            answer_text=answer_text,
            input_mode=input_mode,
            duration_seconds=duration_seconds,
        )
        speech_metrics = SpeechMetricsRecord.model_validate(speech_dict)

        now = datetime.now(timezone.utc)
        pending_record = {
            "question_id": question_id,
            "submission_id": submission_id,
            "answer_text": answer_text,
            "submitted_at": now,
            "evaluation_status": "pending",
            "evaluation": None,
            "evaluated_at": None,
            "evaluation_error": None,
            "speech_metrics": speech_metrics.model_dump(),
        }
        index = int(document["current_question_index"])
        updated = await interview_repo.append_answer_pending(
            session_id,
            user_id,
            index,
            pending_record,
        )
        if updated is None:
            document = await interview_repo.find_by_id_for_user(session_id, user_id)
            if document is None:
                raise InterviewServiceError("Interview session not found", status_code=404)
            dup = interview_repo.find_answer_by_submission(
                document, question_id, submission_id
            )
            if dup is not None:
                return _session_to_response(document)
            latest = interview_repo.find_answer_for_question(document, question_id)
            if latest and latest.get("evaluation_status") == "evaluated":
                raise InterviewServiceError(
                    "This question has already been answered.", status_code=409
                )
            raise InterviewServiceError(
                "Could not save answer. Please retry.", status_code=409
            )
        document = updated

    try:
        evaluation = evaluate_answer_text(
            role=document["role"],
            question=question["question"],
            category=question.get("category", "general"),
            evaluates=question.get("evaluates", "Role fit"),
            answer_text=answer_text,
            language_settings=resolve_language_settings(document),
        )
        evaluation_dict = _evaluation_to_dict(evaluation)
        if billing_repo is not None:
            plan_id = await effective_plan_id(billing_repo, user_id)
            evaluation_dict = redact_coaching_if_needed(evaluation_dict, plan_id)
        parent_index = int(document.get("current_question_index", 0))
        document = await interview_repo.update_answer_evaluation(
            session_id,
            user_id,
            question_id,
            submission_id,
            evaluation_status="evaluated",
            evaluation=evaluation_dict,
            evaluation_error=None,
            advance_index=False,
        )
        if document is not None:
            follow_up_session = await maybe_insert_follow_up(
                session=document,
                parent_question=question,
                answer_text=answer_text,
                evaluation=_evaluation_to_dict(evaluation),
                interview_repo=interview_repo,
                session_id=session_id,
                user_id=user_id,
            )
            if follow_up_session is not None:
                document = follow_up_session
            else:
                advanced = await interview_repo.advance_question_index(
                    session_id,
                    user_id,
                    expected_index=parent_index,
                )
                if advanced is not None:
                    document = advanced
    except (AnswerEvaluationUnavailableError, AnswerEvaluationError) as exc:
        document = await interview_repo.update_answer_evaluation(
            session_id,
            user_id,
            question_id,
            submission_id,
            evaluation_status="failed",
            evaluation=None,
            evaluation_error=str(exc),
            advance_index=False,
        )
        if document is None:
            raise InterviewServiceError(
                "Answer saved but session update failed.", status_code=500
            )
        return _session_to_response(document)

    if document is None:
        raise InterviewServiceError("Failed to update session.", status_code=500)

    return _session_to_response(document)


async def skip_current_follow_up(
    user_id: str,
    session_id: str,
    question_id: str,
    interview_repo: InterviewRepository,
) -> InterviewSessionResponse:
    try:
        updated = await skip_follow_up_question(
            user_id, session_id, question_id, interview_repo
        )
    except FollowUpServiceError as exc:
        raise InterviewServiceError(str(exc), status_code=exc.status_code) from exc
    return _session_to_response(updated)


async def complete_interview_session(
    user_id: str,
    session_id: str,
    interview_repo: InterviewRepository,
) -> InterviewSessionResponse:
    document = await interview_repo.find_by_id_for_user(session_id, user_id)
    if document is None:
        raise InterviewServiceError("Interview session not found", status_code=404)
    if document.get("status") == "completed":
        return _session_to_response(document)
    if document.get("status") != "in_progress":
        raise InterviewServiceError("Invalid session state.", status_code=409)

    questions = document.get("questions", [])
    answers = document.get("answers", [])
    if any(a.get("evaluation_status") in ("pending", "failed") for a in answers):
        raise InterviewServiceError(
            "Resolve pending or failed evaluations before completing.",
            status_code=422,
        )
    evaluated = [
        a
        for a in answers
        if a.get("evaluation_status") == "evaluated" and a.get("evaluation")
    ]
    answered_ids = {a["question_id"] for a in evaluated}
    for question in questions:
        if question.get("skipped"):
            continue
        if question["id"] not in answered_ids:
            raise InterviewServiceError(
                "Answer all questions before completing the interview.",
                status_code=422,
            )

    scores = [a["evaluation"]["overall_score"] for a in evaluated]
    average = round(sum(scores) / len(scores), 1) if scores else None

    highlights: list[str] = []
    focus_areas: list[str] = []
    for answer in evaluated[-3:]:
        evaluation = answer.get("evaluation") or {}
        for item in evaluation.get("strengths", [])[:2]:
            if item not in highlights:
                highlights.append(item)
        for item in evaluation.get("missing_concepts", [])[:2]:
            if item not in focus_areas:
                focus_areas.append(item)

    summary = InterviewSessionSummary(
        total_questions=len(questions),
        answered_questions=len(evaluated),
        average_score=average,
        highlights=highlights[:6],
        focus_areas=focus_areas[:6],
    ).model_dump()

    try:
        completed = await interview_repo.complete_session(session_id, user_id, summary)
    except InterviewRepositoryError:
        raise InterviewServiceError(
            "Unable to complete interview session.", status_code=500
        ) from None

    if completed is None:
        document = await interview_repo.find_by_id_for_user(session_id, user_id)
        if document and document.get("status") == "completed":
            return _session_to_response(document)
        raise InterviewServiceError("Unable to complete interview session.", status_code=409)

    return _session_to_response(completed)
