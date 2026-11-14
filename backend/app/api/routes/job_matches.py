from fastapi import APIRouter, Depends, Header, HTTPException, status

from core.dependencies import (
    get_analysis_repository,
    get_billing_repository,
    get_credit_repository,
    get_current_user,
    get_job_match_repository,
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
from repositories.job_match_repository import JobMatchRepository
from repositories.resume_repository import ResumeRepository
from schemas.job_match_schema import (
    CreateJobMatchRequest,
    JobMatchListResponse,
    JobMatchResponse,
)
from services.job_match_service import (
    JobMatchServiceError,
    create_job_match,
    get_job_match,
    list_job_matches,
)

router = APIRouter()


@router.post(
    "",
    response_model=JobMatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_job_match_endpoint(
    payload: CreateJobMatchRequest,
    current_user: UserPublic = Depends(get_current_user),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repository),
    job_match_repo: JobMatchRepository = Depends(get_job_match_repository),
    billing_repo: BillingRepository = Depends(get_billing_repository),
    credit_repo: CreditRepository = Depends(get_credit_repository),
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
) -> JobMatchResponse:
    charge_key = resolve_idempotency_key(x_idempotency_key)
    try:
        await require_feature(billing_repo, current_user.id, "job_matching")
        await ensure_ai_operation_allowed(
            billing_repo,
            credit_repo,
            current_user.id,
            "job_match",
            idempotency_key=charge_key,
        )
        return await create_job_match(
            user_id=current_user.id,
            payload=payload,
            resume_repo=resume_repo,
            analysis_repo=analysis_repo,
            job_match_repo=job_match_repo,
        )
    except EntitlementError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    except CreditServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    except JobMatchServiceError as exc:
        await safe_refund_ai_operation(
            billing_repo,
            credit_repo,
            current_user.id,
            idempotency_key=charge_key,
            reason="job_match_failed",
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.get("", response_model=JobMatchListResponse)
async def list_job_matches_endpoint(
    current_user: UserPublic = Depends(get_current_user),
    job_match_repo: JobMatchRepository = Depends(get_job_match_repository),
) -> JobMatchListResponse:
    return await list_job_matches(current_user.id, job_match_repo)


@router.get("/{match_id}", response_model=JobMatchResponse)
async def get_job_match_endpoint(
    match_id: str,
    current_user: UserPublic = Depends(get_current_user),
    job_match_repo: JobMatchRepository = Depends(get_job_match_repository),
) -> JobMatchResponse:
    try:
        return await get_job_match(current_user.id, match_id, job_match_repo)
    except JobMatchServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
