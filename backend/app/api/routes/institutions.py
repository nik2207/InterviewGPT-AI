from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi import status as http_status

from core.dependencies import (
    get_current_user,
    get_institution_analytics_repository,
    get_institution_audit_repository,
    get_institution_repository,
    get_interview_repository,
    get_user_repository,
)
from repositories.institution_analytics_repository import InstitutionAnalyticsRepository
from repositories.institution_audit_repository import InstitutionAuditRepository
from schemas.institution_analytics_schema import (
    InstitutionAnalyticsDashboard,
    InstitutionAnalyticsFilters,
    InstitutionAuditListResponse,
    InstitutionSubscriptionView,
    PaginatedMemberListResponse,
)
from models.user_model import UserPublic
from repositories.institution_repository import InstitutionRepository
from repositories.interview_repository import InterviewRepository
from repositories.user_repository import UserRepository
from schemas.institution_schema import (
    AcceptInvitationRequest,
    AssignmentCompletionRequest,
    AssignmentListResponse,
    AssignmentResponse,
    CohortListResponse,
    CohortMemberRequest,
    CohortResponse,
    CreateAssignmentRequest,
    CreateCohortRequest,
    CreateInstitutionRequest,
    CreateInvitationRequest,
    InstitutionAnalyticsOverview,
    InstitutionMemberListResponse,
    InstitutionProfileResponse,
    InvitationResponse,
    MembershipResponse,
    MyMembershipItem,
    StudentProgressSnapshot,
    UpdateInstitutionRequest,
    UpdateMemberRequest,
)
from services.institution_admin_service import (
    get_subscription_view,
    list_audit_log,
    list_members_admin,
    record_admin_action,
    remove_member,
    update_subscription_plan,
)
from services.institution_analytics_service import (
    build_analytics_dashboard,
    build_report,
    export_report_csv,
    export_report_pdf,
)
from services.institution_service import (
    InstitutionServiceError,
    accept_invitation,
    add_student_to_cohort,
    build_analytics_overview,
    build_student_progress_snapshots,
    complete_assignment,
    create_assignment,
    create_cohort,
    create_institution_for_user,
    export_aggregate_csv,
    get_institution_profile,
    invite_member,
    list_institution_assignments,
    list_institution_cohorts,
    list_institution_members,
    list_my_memberships,
    update_institution_member,
    update_institution_profile,
)

router = APIRouter()


def _http(exc: InstitutionServiceError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("", response_model=InstitutionProfileResponse, status_code=http_status.HTTP_201_CREATED)
async def create_institution_endpoint(
    payload: CreateInstitutionRequest,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
    audit_repo: InstitutionAuditRepository = Depends(get_institution_audit_repository),
) -> InstitutionProfileResponse:
    try:
        data = await create_institution_for_user(
            repo, current_user, payload.model_dump()
        )
        await record_admin_action(
            audit_repo,
            data["id"],
            current_user,
            "institution_created",
            {"name": payload.name},
        )
    except InstitutionServiceError as exc:
        raise _http(exc) from None
    return InstitutionProfileResponse.model_validate(data)


@router.get("/me/memberships", response_model=list[MyMembershipItem])
async def my_memberships_endpoint(
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
) -> list[MyMembershipItem]:
    items = await list_my_memberships(repo, current_user)
    return [MyMembershipItem.model_validate(item) for item in items]


@router.post("/invitations/accept", response_model=MembershipResponse)
async def accept_invitation_endpoint(
    payload: AcceptInvitationRequest,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
) -> MembershipResponse:
    try:
        data = await accept_invitation(repo, current_user, payload.token)
    except InstitutionServiceError as exc:
        raise _http(exc) from None
    return MembershipResponse.model_validate(data)


@router.get("/{institution_id}", response_model=InstitutionProfileResponse)
async def get_institution_endpoint(
    institution_id: str,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
) -> InstitutionProfileResponse:
    try:
        data = await get_institution_profile(repo, institution_id, current_user)
    except InstitutionServiceError as exc:
        raise _http(exc) from None
    return InstitutionProfileResponse.model_validate(data)


@router.patch("/{institution_id}", response_model=InstitutionProfileResponse)
async def update_institution_endpoint(
    institution_id: str,
    payload: UpdateInstitutionRequest,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
) -> InstitutionProfileResponse:
    try:
        data = await update_institution_profile(
            repo, institution_id, current_user, payload.model_dump()
        )
    except InstitutionServiceError as exc:
        raise _http(exc) from None
    return InstitutionProfileResponse.model_validate(data)


@router.post("/{institution_id}/invitations", response_model=InvitationResponse)
async def create_invitation_endpoint(
    institution_id: str,
    payload: CreateInvitationRequest,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
) -> InvitationResponse:
    try:
        data = await invite_member(
            repo, institution_id, current_user, payload.model_dump()
        )
    except InstitutionServiceError as exc:
        raise _http(exc) from None
    return InvitationResponse.model_validate(data)


@router.get("/{institution_id}/members", response_model=InstitutionMemberListResponse)
async def list_members_endpoint(
    institution_id: str,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
) -> InstitutionMemberListResponse:
    try:
        items = await list_institution_members(repo, institution_id, current_user)
    except InstitutionServiceError as exc:
        raise _http(exc) from None
    return InstitutionMemberListResponse(
        items=[MembershipResponse.model_validate(row) for row in items],
        total=len(items),
    )


@router.patch("/{institution_id}/members/{membership_id}", response_model=MembershipResponse)
async def update_member_endpoint(
    institution_id: str,
    membership_id: str,
    payload: UpdateMemberRequest,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
) -> MembershipResponse:
    try:
        data = await update_institution_member(
            repo,
            institution_id,
            current_user,
            membership_id,
            payload.model_dump(),
        )
    except InstitutionServiceError as exc:
        raise _http(exc) from None
    return MembershipResponse.model_validate(data)


@router.post("/{institution_id}/cohorts", response_model=CohortResponse, status_code=http_status.HTTP_201_CREATED)
async def create_cohort_endpoint(
    institution_id: str,
    payload: CreateCohortRequest,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
) -> CohortResponse:
    try:
        data = await create_cohort(
            repo, institution_id, current_user, payload.model_dump()
        )
    except InstitutionServiceError as exc:
        raise _http(exc) from None
    return CohortResponse.model_validate(data)


@router.get("/{institution_id}/cohorts", response_model=CohortListResponse)
async def list_cohorts_endpoint(
    institution_id: str,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
) -> CohortListResponse:
    try:
        items = await list_institution_cohorts(repo, institution_id, current_user)
    except InstitutionServiceError as exc:
        raise _http(exc) from None
    return CohortListResponse(
        items=[CohortResponse.model_validate(row) for row in items],
        total=len(items),
    )


@router.post("/{institution_id}/cohorts/{cohort_id}/members", status_code=http_status.HTTP_204_NO_CONTENT)
async def add_cohort_member_endpoint(
    institution_id: str,
    cohort_id: str,
    payload: CohortMemberRequest,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
) -> None:
    try:
        await add_student_to_cohort(
            repo, institution_id, cohort_id, current_user, payload.user_id
        )
    except InstitutionServiceError as exc:
        raise _http(exc) from None


@router.post(
    "/{institution_id}/assignments",
    response_model=AssignmentResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def create_assignment_endpoint(
    institution_id: str,
    payload: CreateAssignmentRequest,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
) -> AssignmentResponse:
    try:
        data = await create_assignment(
            repo, institution_id, current_user, payload.model_dump()
        )
    except InstitutionServiceError as exc:
        raise _http(exc) from None
    return AssignmentResponse.model_validate(data)


@router.get("/{institution_id}/assignments", response_model=AssignmentListResponse)
async def list_assignments_endpoint(
    institution_id: str,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
) -> AssignmentListResponse:
    try:
        items = await list_institution_assignments(repo, institution_id, current_user)
    except InstitutionServiceError as exc:
        raise _http(exc) from None
    return AssignmentListResponse(
        items=[AssignmentResponse.model_validate(row) for row in items],
        total=len(items),
    )


@router.post("/{institution_id}/assignments/{assignment_id}/complete", response_model=AssignmentResponse)
async def complete_assignment_endpoint(
    institution_id: str,
    assignment_id: str,
    payload: AssignmentCompletionRequest,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
) -> AssignmentResponse:
    try:
        data = await complete_assignment(
            repo, institution_id, assignment_id, current_user, payload.notes
        )
    except InstitutionServiceError as exc:
        raise _http(exc) from None
    return AssignmentResponse.model_validate(data)


@router.get("/{institution_id}/analytics/overview", response_model=InstitutionAnalyticsOverview)
async def analytics_overview_endpoint(
    institution_id: str,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
    analytics_repo: InstitutionAnalyticsRepository = Depends(
        get_institution_analytics_repository
    ),
) -> InstitutionAnalyticsOverview:
    try:
        data = await build_analytics_overview(
            repo,
            interview_repo,
            institution_id,
            current_user,
            analytics_repo=analytics_repo,
        )
    except InstitutionServiceError as exc:
        raise _http(exc) from None
    return InstitutionAnalyticsOverview.model_validate(data)


@router.get("/{institution_id}/analytics/dashboard", response_model=InstitutionAnalyticsDashboard)
async def analytics_dashboard_endpoint(
    institution_id: str,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
    analytics_repo: InstitutionAnalyticsRepository = Depends(
        get_institution_analytics_repository
    ),
    department: str = "",
    course: str = "",
    batch_label: str = "",
    cohort_id: str | None = None,
    job_role: str = "",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> InstitutionAnalyticsDashboard:
    filters = InstitutionAnalyticsFilters(
        department=department,
        course=course,
        batch_label=batch_label,
        cohort_id=cohort_id,
        job_role=job_role,
        date_from=date_from,
        date_to=date_to,
    )
    try:
        data = await build_analytics_dashboard(
            repo, analytics_repo, institution_id, current_user, filters
        )
    except InstitutionServiceError as exc:
        raise _http(exc) from None
    return InstitutionAnalyticsDashboard.model_validate(data)


@router.get("/{institution_id}/reports/export")
async def export_report_endpoint(
    institution_id: str,
    report_type: str = "summary",
    export_format: str = "csv",
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
    analytics_repo: InstitutionAnalyticsRepository = Depends(
        get_institution_analytics_repository
    ),
    department: str = "",
    course: str = "",
    batch_label: str = "",
    cohort_id: str | None = None,
    job_role: str = "",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> Response:
    filters = InstitutionAnalyticsFilters(
        department=department,
        course=course,
        batch_label=batch_label,
        cohort_id=cohort_id,
        job_role=job_role,
        date_from=date_from,
        date_to=date_to,
    )
    try:
        report = await build_report(
            repo, analytics_repo, institution_id, current_user, report_type, filters
        )
    except InstitutionServiceError as exc:
        raise _http(exc) from None
    if export_format == "pdf":
        pdf_bytes = export_report_pdf(report)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="institution-{institution_id}-{report_type}.pdf"'
            },
        )
    csv_text = export_report_csv(report)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="institution-{institution_id}-{report_type}.csv"'
        },
    )


@router.get("/{institution_id}/reports/{report_type}")
async def institution_report_endpoint(
    institution_id: str,
    report_type: str,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
    analytics_repo: InstitutionAnalyticsRepository = Depends(
        get_institution_analytics_repository
    ),
    department: str = "",
    course: str = "",
    batch_label: str = "",
    cohort_id: str | None = None,
    job_role: str = "",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict:
    filters = InstitutionAnalyticsFilters(
        department=department,
        course=course,
        batch_label=batch_label,
        cohort_id=cohort_id,
        job_role=job_role,
        date_from=date_from,
        date_to=date_to,
    )
    try:
        return await build_report(
            repo, analytics_repo, institution_id, current_user, report_type, filters
        )
    except InstitutionServiceError as exc:
        raise _http(exc) from None


@router.get("/{institution_id}/admin/members", response_model=PaginatedMemberListResponse)
async def admin_members_paginated_endpoint(
    institution_id: str,
    page: int = 1,
    page_size: int = 25,
    role: str | None = None,
    department: str | None = None,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
) -> PaginatedMemberListResponse:
    try:
        data = await list_members_admin(
            repo,
            institution_id,
            current_user,
            page=page,
            page_size=page_size,
            role=role,
            department=department,
        )
    except InstitutionServiceError as exc:
        raise _http(exc) from None
    return PaginatedMemberListResponse.model_validate(data)


@router.post("/{institution_id}/admin/members/{membership_id}/remove", response_model=MembershipResponse)
async def admin_remove_member_endpoint(
    institution_id: str,
    membership_id: str,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
    audit_repo: InstitutionAuditRepository = Depends(get_institution_audit_repository),
) -> MembershipResponse:
    try:
        data = await remove_member(
            audit_repo, repo, institution_id, current_user, membership_id
        )
    except InstitutionServiceError as exc:
        raise _http(exc) from None
    return MembershipResponse.model_validate(data)


@router.get("/{institution_id}/admin/audit", response_model=InstitutionAuditListResponse)
async def admin_audit_endpoint(
    institution_id: str,
    page: int = 1,
    page_size: int = 25,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
    audit_repo: InstitutionAuditRepository = Depends(get_institution_audit_repository),
) -> InstitutionAuditListResponse:
    try:
        data = await list_audit_log(
            audit_repo, repo, institution_id, current_user, page=page, page_size=page_size
        )
    except InstitutionServiceError as exc:
        raise _http(exc) from None
    return InstitutionAuditListResponse.model_validate(data)


@router.get("/{institution_id}/admin/subscription", response_model=InstitutionSubscriptionView)
async def admin_subscription_endpoint(
    institution_id: str,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
) -> InstitutionSubscriptionView:
    try:
        data = await get_subscription_view(repo, institution_id, current_user)
    except InstitutionServiceError as exc:
        raise _http(exc) from None
    return InstitutionSubscriptionView.model_validate(data)


@router.patch("/{institution_id}/admin/subscription", response_model=InstitutionSubscriptionView)
async def admin_update_subscription_endpoint(
    institution_id: str,
    plan_id: str,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
    audit_repo: InstitutionAuditRepository = Depends(get_institution_audit_repository),
) -> InstitutionSubscriptionView:
    try:
        data = await update_subscription_plan(
            audit_repo, repo, institution_id, current_user, plan_id
        )
    except InstitutionServiceError as exc:
        raise _http(exc) from None
    return InstitutionSubscriptionView.model_validate(data)


@router.get("/{institution_id}/progress/students", response_model=list[StudentProgressSnapshot])
async def student_progress_endpoint(
    institution_id: str,
    cohort_id: str | None = None,
    current_user: UserPublic = Depends(get_current_user),
    repo: InstitutionRepository = Depends(get_institution_repository),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> list[StudentProgressSnapshot]:
    try:
        items = await build_student_progress_snapshots(
            repo,
            interview_repo,
            user_repo,
            institution_id,
            current_user,
            cohort_id=cohort_id,
        )
    except InstitutionServiceError as exc:
        raise _http(exc) from None
    return [StudentProgressSnapshot.model_validate(row) for row in items]
