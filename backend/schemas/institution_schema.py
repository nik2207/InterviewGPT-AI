from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

InstitutionRole = Literal[
    "institution_admin",
    "placement_officer",
    "trainer",
    "student",
]

InstitutionStatus = Literal["active", "suspended"]
InvitationStatus = Literal["pending", "accepted", "revoked", "expired"]
AssignmentActivityType = Literal[
    "mock_interview",
    "resume_analysis",
    "job_match",
    "preparation_plan",
    "custom",
]


class InstitutionProfileResponse(BaseModel):
    id: str
    name: str
    slug: str
    institution_type: str = ""
    website: str = ""
    department: str = ""
    course_metadata: dict = Field(default_factory=dict)
    status: InstitutionStatus
    created_at: datetime
    updated_at: datetime


class CreateInstitutionRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    institution_type: str = Field(default="", max_length=80)
    website: str = Field(default="", max_length=200)
    department: str = Field(default="", max_length=120)
    course_metadata: dict = Field(default_factory=dict)


class UpdateInstitutionRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    institution_type: str | None = Field(default=None, max_length=80)
    website: str | None = Field(default=None, max_length=200)
    department: str | None = Field(default=None, max_length=120)
    course_metadata: dict | None = None


class MembershipResponse(BaseModel):
    id: str
    institution_id: str
    user_id: str
    role: InstitutionRole
    department: str = ""
    course: str = ""
    batch_label: str = ""
    consent_share_progress: bool = False
    status: Literal["active", "invited", "removed"] = "active"
    created_at: datetime


class MyMembershipItem(BaseModel):
    institution: InstitutionProfileResponse
    membership: MembershipResponse


class CreateInvitationRequest(BaseModel):
    email: EmailStr
    role: InstitutionRole = "student"
    department: str = Field(default="", max_length=120)
    course: str = Field(default="", max_length=120)
    batch_label: str = Field(default="", max_length=80)


class InvitationResponse(BaseModel):
    id: str
    institution_id: str
    email: str
    role: InstitutionRole
    status: InvitationStatus
    expires_at: datetime
    invite_token: str | None = None


class AcceptInvitationRequest(BaseModel):
    token: str = Field(..., min_length=16, max_length=128)


class UpdateMemberRequest(BaseModel):
    role: InstitutionRole | None = None
    department: str | None = Field(default=None, max_length=120)
    course: str | None = Field(default=None, max_length=120)
    batch_label: str | None = Field(default=None, max_length=80)
    consent_share_progress: bool | None = None
    status: Literal["active", "removed"] | None = None


class CreateCohortRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    department: str = Field(default="", max_length=120)
    course: str = Field(default="", max_length=120)
    academic_year: str = Field(default="", max_length=40)
    description: str = Field(default="", max_length=500)


class CohortResponse(BaseModel):
    id: str
    institution_id: str
    name: str
    department: str = ""
    course: str = ""
    academic_year: str = ""
    description: str = ""
    member_count: int = 0
    created_at: datetime


class CohortMemberRequest(BaseModel):
    user_id: str = Field(..., min_length=8, max_length=32)


class CreateAssignmentRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=160)
    activity_type: AssignmentActivityType = "mock_interview"
    cohort_id: str | None = None
    description: str = Field(default="", max_length=1000)
    due_at: datetime | None = None
    job_role: str = Field(default="", max_length=120)
    metadata: dict = Field(default_factory=dict)


class AssignmentResponse(BaseModel):
    id: str
    institution_id: str
    cohort_id: str | None
    title: str
    activity_type: AssignmentActivityType
    description: str = ""
    due_at: datetime | None
    job_role: str = ""
    created_by: str
    created_at: datetime
    completion_count: int = 0
    assigned_count: int = 0


class AssignmentCompletionRequest(BaseModel):
    notes: str = Field(default="", max_length=500)


class StudentProgressSnapshot(BaseModel):
    user_id: str
    display_name: str
    email: str | None = None
    interviews_completed: int = 0
    average_interview_score: float | None = None
    assignments_completed: int = 0
    assignments_total: int = 0
    consent_share_progress: bool = False
    detail_level: Literal["aggregate", "individual"] = "aggregate"


class InstitutionAnalyticsOverview(BaseModel):
    institution_id: str
    student_count: int
    cohort_count: int
    active_assignments: int
    assignment_completion_rate: float
    average_interview_score: float | None
    readiness_trend: list[dict]
    privacy_note: str


class InstitutionMemberListResponse(BaseModel):
    items: list[MembershipResponse]
    total: int


class CohortListResponse(BaseModel):
    items: list[CohortResponse]
    total: int


class AssignmentListResponse(BaseModel):
    items: list[AssignmentResponse]
    total: int
