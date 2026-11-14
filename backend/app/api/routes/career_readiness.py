from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import Response

from core.dependencies import (
    get_analysis_repository,
    get_billing_repository,
    get_credit_repository,
    get_career_readiness_repository,
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
from repositories.career_readiness_repository import CareerReadinessRepository
from repositories.interview_repository import InterviewRepository
from repositories.job_match_repository import JobMatchRepository
from repositories.preparation_plan_repository import PreparationPlanRepository
from repositories.resume_repository import ResumeRepository
from schemas.career_readiness_schema import (
    CareerReadinessReportListResponse,
    CareerReadinessReportResponse,
    GenerateCareerReadinessRequest,
)
from services.career_readiness_report_pdf import generate_career_readiness_pdf
from services.career_readiness_service import (
    CareerReadinessServiceError,
    generate_and_save_report,
    get_saved_report,
    list_reports,
)

router = APIRouter()


@router.post(
    "/reports",
    response_model=CareerReadinessReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_readiness_report_endpoint(
    payload: GenerateCareerReadinessRequest,
    current_user: UserPublic = Depends(get_current_user),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repository),
    job_match_repo: JobMatchRepository = Depends(get_job_match_repository),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
    plan_repo: PreparationPlanRepository = Depends(get_preparation_plan_repository),
    readiness_repo: CareerReadinessRepository = Depends(get_career_readiness_repository),
    billing_repo: BillingRepository = Depends(get_billing_repository),
    credit_repo: CreditRepository = Depends(get_credit_repository),
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
) -> CareerReadinessReportResponse:
    charge_key = resolve_idempotency_key(x_idempotency_key)
    try:
        await require_feature(billing_repo, current_user.id, "career_readiness")
        await ensure_ai_operation_allowed(
            billing_repo,
            credit_repo,
            current_user.id,
            "career_readiness_report",
            idempotency_key=charge_key,
        )
        return await generate_and_save_report(
            user_id=current_user.id,
            payload=payload,
            resume_repo=resume_repo,
            analysis_repo=analysis_repo,
            job_match_repo=job_match_repo,
            interview_repo=interview_repo,
            plan_repo=plan_repo,
            readiness_repo=readiness_repo,
        )
    except EntitlementError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    except CreditServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    except CareerReadinessServiceError as exc:
        await safe_refund_ai_operation(
            billing_repo,
            credit_repo,
            current_user.id,
            idempotency_key=charge_key,
            reason="career_readiness_failed",
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.get("/reports", response_model=CareerReadinessReportListResponse)
async def list_readiness_reports_endpoint(
    current_user: UserPublic = Depends(get_current_user),
    readiness_repo: CareerReadinessRepository = Depends(get_career_readiness_repository),
) -> CareerReadinessReportListResponse:
    return await list_reports(current_user.id, readiness_repo)


@router.get("/reports/{report_id}", response_model=CareerReadinessReportResponse)
async def get_readiness_report_endpoint(
    report_id: str,
    current_user: UserPublic = Depends(get_current_user),
    readiness_repo: CareerReadinessRepository = Depends(get_career_readiness_repository),
) -> CareerReadinessReportResponse:
    try:
        return await get_saved_report(current_user.id, report_id, readiness_repo)
    except CareerReadinessServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.get("/reports/{report_id}/pdf")
async def download_readiness_report_pdf(
    report_id: str,
    current_user: UserPublic = Depends(get_current_user),
    readiness_repo: CareerReadinessRepository = Depends(get_career_readiness_repository),
) -> Response:
    try:
        report = await get_saved_report(current_user.id, report_id, readiness_repo)
    except CareerReadinessServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None

    pdf_bytes = generate_career_readiness_pdf(report)
    safe_id = report_id[:12]
    filename = f"career-readiness-{safe_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
