from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ReportType = Literal[
    "summary",
    "cohort_performance",
    "participation",
    "skill_gaps",
    "assignments",
]


class InstitutionAnalyticsFilters(BaseModel):
    department: str = ""
    course: str = ""
    batch_label: str = ""
    cohort_id: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    job_role: str = ""


class AnalyticsMetricCard(BaseModel):
    label: str
    value: str | int | float | None
    sample_size: int | None = None
    suppressed: bool = False
    note: str = ""


class CohortComparisonItem(BaseModel):
    cohort_id: str
    cohort_name: str
    sample_size: int
    sessions_completed: int | None = None
    average_score: float | None = None
    assignment_completion_rate: float | None = None
    suppressed: bool = False


class InstitutionAnalyticsDashboard(BaseModel):
    institution_id: str
    reporting_period: dict
    filters_applied: InstitutionAnalyticsFilters
    disclaimer: str
    not_hiring_outcome_note: str
    total_enrolled_students: int
    active_students: int | None
    practice_sessions_completed: int
    average_interview_score: float | None
    assignment_completion_rate: float
    preparation_plan_completion_rate: float | None
    skill_distribution: dict[str, float]
    common_skill_gaps: list[dict]
    monthly_activity_trend: list[dict]
    cohort_comparisons: list[CohortComparisonItem]
    cards: list[AnalyticsMetricCard]


class InstitutionSubscriptionView(BaseModel):
    institution_id: str
    subscription_plan: str
    seat_limit: int
    seats_used: int
    features: list[str]
    disclaimer: str


class InstitutionAuditItem(BaseModel):
    id: str
    action: str
    actor_user_id: str
    detail: dict
    created_at: datetime


class InstitutionAuditListResponse(BaseModel):
    items: list[InstitutionAuditItem]
    total: int
    page: int
    page_size: int


class PaginatedMemberListResponse(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int


class InstitutionReportExportQuery(BaseModel):
    report_type: ReportType = "summary"
    format: Literal["csv", "pdf"] = "csv"
