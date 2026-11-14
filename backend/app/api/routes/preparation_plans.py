from fastapi import APIRouter, Depends, Header, HTTPException, status

from core.dependencies import (
    get_analysis_repository,
    get_billing_repository,
    get_credit_repository,
    get_current_user,
    get_interview_repository,
    get_job_match_repository,
    get_preparation_plan_repository,
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
from repositories.job_match_repository import JobMatchRepository
from repositories.preparation_plan_repository import PreparationPlanRepository
from repositories.resume_repository import ResumeRepository
from schemas.preparation_plan_schema import (
    GeneratePreparationPlanRequest,
    PreparationPlanListResponse,
    PreparationPlanResponse,
    UpdatePlanTaskCompletionRequest,
)
from services.preparation_plan_service import (
    PreparationPlanServiceError,
    archive_preparation_plan,
    generate_preparation_plan,
    get_preparation_plan,
    list_preparation_plans,
    regenerate_preparation_plan,
    update_task_completion,
)

router = APIRouter()


@router.post(
    "",
    response_model=PreparationPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_preparation_plan_endpoint(
    payload: GeneratePreparationPlanRequest,
    current_user: UserPublic = Depends(get_current_user),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repository),
    job_match_repo: JobMatchRepository = Depends(get_job_match_repository),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
    plan_repo: PreparationPlanRepository = Depends(get_preparation_plan_repository),
    billing_repo: BillingRepository = Depends(get_billing_repository),
    credit_repo: CreditRepository = Depends(get_credit_repository),
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
) -> PreparationPlanResponse:
    charge_key = resolve_idempotency_key(x_idempotency_key)
    try:
        await require_feature(billing_repo, current_user.id, "preparation_plans")
        await ensure_ai_operation_allowed(
            billing_repo,
            credit_repo,
            current_user.id,
            "preparation_plan",
            idempotency_key=charge_key,
        )
        return await generate_preparation_plan(
            user_id=current_user.id,
            payload=payload,
            resume_repo=resume_repo,
            analysis_repo=analysis_repo,
            job_match_repo=job_match_repo,
            interview_repo=interview_repo,
            plan_repo=plan_repo,
        )
    except EntitlementError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    except CreditServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    except PreparationPlanServiceError as exc:
        await safe_refund_ai_operation(
            billing_repo,
            credit_repo,
            current_user.id,
            idempotency_key=charge_key,
            reason="preparation_plan_failed",
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.get("", response_model=PreparationPlanListResponse)
async def list_preparation_plans_endpoint(
    current_user: UserPublic = Depends(get_current_user),
    plan_repo: PreparationPlanRepository = Depends(get_preparation_plan_repository),
) -> PreparationPlanListResponse:
    return await list_preparation_plans(current_user.id, plan_repo)


@router.get("/{plan_id}", response_model=PreparationPlanResponse)
async def get_preparation_plan_endpoint(
    plan_id: str,
    current_user: UserPublic = Depends(get_current_user),
    plan_repo: PreparationPlanRepository = Depends(get_preparation_plan_repository),
) -> PreparationPlanResponse:
    try:
        return await get_preparation_plan(current_user.id, plan_id, plan_repo)
    except PreparationPlanServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.patch(
    "/{plan_id}/days/{day_number}/tasks/{task_id}",
    response_model=PreparationPlanResponse,
)
async def update_plan_task_endpoint(
    plan_id: str,
    day_number: int,
    task_id: str,
    payload: UpdatePlanTaskCompletionRequest,
    current_user: UserPublic = Depends(get_current_user),
    plan_repo: PreparationPlanRepository = Depends(get_preparation_plan_repository),
) -> PreparationPlanResponse:
    try:
        return await update_task_completion(
            user_id=current_user.id,
            plan_id=plan_id,
            day_number=day_number,
            task_id=task_id,
            payload=payload,
            plan_repo=plan_repo,
        )
    except PreparationPlanServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.post("/{plan_id}/archive", response_model=PreparationPlanResponse)
async def archive_preparation_plan_endpoint(
    plan_id: str,
    current_user: UserPublic = Depends(get_current_user),
    plan_repo: PreparationPlanRepository = Depends(get_preparation_plan_repository),
) -> PreparationPlanResponse:
    try:
        return await archive_preparation_plan(current_user.id, plan_id, plan_repo)
    except PreparationPlanServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.post(
    "/{plan_id}/regenerate",
    response_model=PreparationPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def regenerate_preparation_plan_endpoint(
    plan_id: str,
    current_user: UserPublic = Depends(get_current_user),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repository),
    job_match_repo: JobMatchRepository = Depends(get_job_match_repository),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
    plan_repo: PreparationPlanRepository = Depends(get_preparation_plan_repository),
    billing_repo: BillingRepository = Depends(get_billing_repository),
    credit_repo: CreditRepository = Depends(get_credit_repository),
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
) -> PreparationPlanResponse:
    charge_key = resolve_idempotency_key(x_idempotency_key)
    try:
        await require_feature(billing_repo, current_user.id, "preparation_plans")
        await ensure_ai_operation_allowed(
            billing_repo,
            credit_repo,
            current_user.id,
            "preparation_plan",
            idempotency_key=f"regen-{plan_id}-{charge_key}",
        )
        return await regenerate_preparation_plan(
            user_id=current_user.id,
            plan_id=plan_id,
            resume_repo=resume_repo,
            analysis_repo=analysis_repo,
            job_match_repo=job_match_repo,
            interview_repo=interview_repo,
            plan_repo=plan_repo,
        )
    except EntitlementError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    except CreditServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    except PreparationPlanServiceError as exc:
        await safe_refund_ai_operation(
            billing_repo,
            credit_repo,
            current_user.id,
            idempotency_key=f"regen-{plan_id}-{charge_key}",
            reason="preparation_plan_regenerate_failed",
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
