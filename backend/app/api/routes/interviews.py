from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import Response

from core.dependencies import (
    get_analysis_repository,
    get_billing_repository,
    get_credit_repository,
    get_current_user,
    get_interview_repository,
    get_resume_repository,
)
from repositories.billing_repository import BillingRepository
from repositories.credit_repository import CreditRepository
from services.credit_idempotency import resolve_idempotency_key
from services.credit_service import (
    CreditServiceError,
    ensure_ai_operation_allowed,
    safe_refund_ai_operation,
)
from services.entitlement_service import EntitlementError, require_feature
from models.user_model import UserPublic
from repositories.analysis_repository import AnalysisRepository
from repositories.interview_repository import InterviewRepository
from repositories.resume_repository import ResumeRepository
from schemas.coaching_schema import CoachingPlanResponse
from schemas.interview_schema import (
    AppendVoiceTranscriptRequest,
    CreateInterviewSessionRequest,
    InterviewHistoryListResponse,
    InterviewSessionListResponse,
    InterviewSessionResponse,
    InterviewTranscriptReviewResponse,
    SubmitAnswerRequest,
    UpdatePracticeRevisionRequest,
    UpdateTranscriptBookmarksRequest,
    UpdateVoiceSessionStatusRequest,
    VoiceClarificationRequest,
    VoiceClarificationResponse,
    VoiceInterviewState,
)
from services.coaching_plan_service import (
    CoachingPlanServiceError,
    generate_coaching_plan_for_session,
)
from services.interview_service import (
    InterviewServiceError,
    complete_interview_session,
    create_interview_session,
    delete_interview_session,
    get_interview_report_pdf,
    get_interview_session,
    get_interview_transcript_pdf,
    get_interview_transcript_review,
    list_interview_history,
    list_interview_sessions,
    save_practice_revision,
    skip_current_follow_up,
    submit_answer,
    update_transcript_bookmarks,
)
from services.voice_interview_service import (
    VoiceInterviewServiceError,
    append_transcript,
    request_clarification,
    update_voice_status,
)

router = APIRouter()


@router.post(
    "",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_endpoint(
    payload: CreateInterviewSessionRequest,
    current_user: UserPublic = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repository),
    billing_repo: BillingRepository = Depends(get_billing_repository),
    credit_repo: CreditRepository = Depends(get_credit_repository),
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
) -> InterviewSessionResponse:
    mock_key = resolve_idempotency_key(x_idempotency_key)
    voice_key = f"voice-{mock_key}"
    try:
        await ensure_ai_operation_allowed(
            billing_repo,
            credit_repo,
            current_user.id,
            "mock_interview_session",
            idempotency_key=mock_key,
        )
        if payload.voice_interview_enabled:
            await require_feature(billing_repo, current_user.id, "voice_interview")
            await ensure_ai_operation_allowed(
                billing_repo,
                credit_repo,
                current_user.id,
                "voice_interview_session",
                idempotency_key=voice_key,
            )
        return await create_interview_session(
            user_id=current_user.id,
            payload=payload,
            interview_repo=interview_repo,
            resume_repo=resume_repo,
            analysis_repo=analysis_repo,
        )
    except EntitlementError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    except CreditServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    except InterviewServiceError as exc:
        await safe_refund_ai_operation(
            billing_repo, credit_repo, current_user.id, idempotency_key=mock_key
        )
        if payload.voice_interview_enabled:
            await safe_refund_ai_operation(
                billing_repo, credit_repo, current_user.id, idempotency_key=voice_key
            )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.get("", response_model=InterviewSessionListResponse)
async def list_sessions_endpoint(
    current_user: UserPublic = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
) -> InterviewSessionListResponse:
    return await list_interview_sessions(current_user.id, interview_repo)


@router.get("/history", response_model=InterviewHistoryListResponse)
async def list_history_endpoint(
    current_user: UserPublic = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
) -> InterviewHistoryListResponse:
    try:
        return await list_interview_history(current_user.id, interview_repo)
    except InterviewServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.get("/{session_id}/coaching-plan", response_model=CoachingPlanResponse)
async def get_coaching_plan_endpoint(
    session_id: str,
    current_user: UserPublic = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repository),
) -> CoachingPlanResponse:
    try:
        return await generate_coaching_plan_for_session(
            current_user.id,
            session_id,
            interview_repo,
            analysis_repo,
        )
    except CoachingPlanServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.get("/{session_id}/report")
async def download_report_endpoint(
    session_id: str,
    current_user: UserPublic = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
    billing_repo: BillingRepository = Depends(get_billing_repository),
    credit_repo: CreditRepository = Depends(get_credit_repository),
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
) -> Response:
    charge_key = resolve_idempotency_key(x_idempotency_key)
    try:
        await ensure_ai_operation_allowed(
            billing_repo,
            credit_repo,
            current_user.id,
            "premium_report_pdf",
            idempotency_key=charge_key,
        )
        pdf_bytes, filename = await get_interview_report_pdf(
            current_user.id, session_id, interview_repo
        )
    except EntitlementError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    except CreditServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    except InterviewServiceError as exc:
        await safe_refund_ai_operation(
            billing_repo, credit_repo, current_user.id, idempotency_key=charge_key
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/{session_id}/transcript/review", response_model=InterviewTranscriptReviewResponse)
async def transcript_review_endpoint(
    session_id: str,
    current_user: UserPublic = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
) -> InterviewTranscriptReviewResponse:
    try:
        return await get_interview_transcript_review(
            current_user.id, session_id, interview_repo
        )
    except InterviewServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.patch("/{session_id}/transcript/bookmarks", response_model=InterviewTranscriptReviewResponse)
async def transcript_bookmarks_endpoint(
    session_id: str,
    payload: UpdateTranscriptBookmarksRequest,
    current_user: UserPublic = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
) -> InterviewTranscriptReviewResponse:
    try:
        return await update_transcript_bookmarks(
            current_user.id, session_id, payload, interview_repo
        )
    except InterviewServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.put(
    "/{session_id}/transcript/practice/{question_id}",
    response_model=InterviewTranscriptReviewResponse,
)
async def transcript_practice_endpoint(
    session_id: str,
    question_id: str,
    payload: UpdatePracticeRevisionRequest,
    current_user: UserPublic = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
) -> InterviewTranscriptReviewResponse:
    try:
        return await save_practice_revision(
            current_user.id, session_id, question_id, payload, interview_repo
        )
    except InterviewServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.get("/{session_id}/transcript/export")
async def transcript_export_endpoint(
    session_id: str,
    current_user: UserPublic = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
) -> Response:
    try:
        pdf_bytes, filename = await get_interview_transcript_pdf(
            current_user.id, session_id, interview_repo
        )
    except InterviewServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session_endpoint(
    session_id: str,
    current_user: UserPublic = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
) -> None:
    try:
        await delete_interview_session(current_user.id, session_id, interview_repo)
    except InterviewServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.get("/{session_id}", response_model=InterviewSessionResponse)
async def get_session_endpoint(
    session_id: str,
    current_user: UserPublic = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
) -> InterviewSessionResponse:
    try:
        return await get_interview_session(
            current_user.id, session_id, interview_repo
        )
    except InterviewServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.post("/{session_id}/answers", response_model=InterviewSessionResponse)
async def submit_answer_endpoint(
    session_id: str,
    payload: SubmitAnswerRequest,
    current_user: UserPublic = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
    billing_repo: BillingRepository = Depends(get_billing_repository),
) -> InterviewSessionResponse:
    try:
        return await submit_answer(
            current_user.id,
            session_id,
            payload,
            interview_repo,
            billing_repo=billing_repo,
        )
    except InterviewServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.post(
    "/{session_id}/questions/{question_id}/skip",
    response_model=InterviewSessionResponse,
)
async def skip_follow_up_endpoint(
    session_id: str,
    question_id: str,
    current_user: UserPublic = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
) -> InterviewSessionResponse:
    try:
        return await skip_current_follow_up(
            current_user.id, session_id, question_id, interview_repo
        )
    except InterviewServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.post("/{session_id}/complete", response_model=InterviewSessionResponse)
async def complete_session_endpoint(
    session_id: str,
    current_user: UserPublic = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
) -> InterviewSessionResponse:
    try:
        return await complete_interview_session(
            current_user.id, session_id, interview_repo
        )
    except InterviewServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.post("/{session_id}/voice/transcript", response_model=VoiceInterviewState)
async def append_voice_transcript_endpoint(
    session_id: str,
    payload: AppendVoiceTranscriptRequest,
    current_user: UserPublic = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
) -> VoiceInterviewState:
    try:
        return await append_transcript(
            current_user.id, session_id, payload, interview_repo
        )
    except VoiceInterviewServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.patch("/{session_id}/voice/status", response_model=VoiceInterviewState)
async def update_voice_status_endpoint(
    session_id: str,
    payload: UpdateVoiceSessionStatusRequest,
    current_user: UserPublic = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
) -> VoiceInterviewState:
    try:
        return await update_voice_status(
            current_user.id, session_id, payload, interview_repo
        )
    except VoiceInterviewServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.post(
    "/{session_id}/voice/clarification",
    response_model=VoiceClarificationResponse,
)
async def voice_clarification_endpoint(
    session_id: str,
    payload: VoiceClarificationRequest,
    current_user: UserPublic = Depends(get_current_user),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
) -> VoiceClarificationResponse:
    try:
        return await request_clarification(
            current_user.id, session_id, payload, interview_repo
        )
    except VoiceInterviewServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
