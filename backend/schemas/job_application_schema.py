from datetime import date, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

ApplicationStatus = Literal[
    "interested",
    "applied",
    "assessment",
    "interview_scheduled",
    "interview_completed",
    "offer_received",
    "rejected",
    "withdrawn",
]

EmploymentType = Literal[
    "full_time",
    "part_time",
    "contract",
    "internship",
    "freelance",
    "other",
]

APPLICATION_STATUS_LABELS = {
    "interested": "Interested",
    "applied": "Applied",
    "assessment": "Assessment",
    "interview_scheduled": "Interview Scheduled",
    "interview_completed": "Interview Completed",
    "offer_received": "Offer Received",
    "rejected": "Rejected",
    "withdrawn": "Withdrawn",
}

JOB_APPLICATION_DISCLAIMER = (
    "This tracker is manual — InterviewGPT does not sync with job boards or email. "
    "Update status yourself when things change."
)


class InterviewDateEntry(BaseModel):
    id: str = Field(
        default_factory=lambda: uuid4().hex[:12], min_length=1, max_length=32
    )
    label: str = Field(default="Interview", min_length=1, max_length=120)
    scheduled_at: datetime
    notes: str = Field(default="", max_length=2000)


class CreateJobApplicationRequest(BaseModel):
    company: str = Field(..., min_length=1, max_length=200)
    job_title: str = Field(..., min_length=1, max_length=200)
    job_description: str = Field(default="", max_length=20000)
    job_posting_url: str | None = Field(default=None, max_length=500)
    location: str = Field(default="", max_length=200)
    employment_type: EmploymentType = "full_time"
    application_date: date | None = None
    status: ApplicationStatus = "interested"
    resume_id: str | None = Field(default=None, max_length=64)
    job_match_id: str | None = Field(default=None, max_length=64)
    interview_dates: list[InterviewDateEntry] = Field(default_factory=list, max_length=20)
    notes: str = Field(default="", max_length=8000)
    follow_up_date: date | None = None

    @field_validator("job_posting_url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        cleaned = value.strip()
        if not cleaned.startswith(("http://", "https://")):
            raise ValueError("Job posting URL must start with http:// or https://")
        if len(cleaned) > 500:
            raise ValueError("Job posting URL is too long.")
        return cleaned


class UpdateJobApplicationRequest(BaseModel):
    company: str | None = Field(default=None, min_length=1, max_length=200)
    job_title: str | None = Field(default=None, min_length=1, max_length=200)
    job_description: str | None = Field(default=None, max_length=20000)
    job_posting_url: str | None = Field(default=None, max_length=500)
    location: str | None = Field(default=None, max_length=200)
    employment_type: EmploymentType | None = None
    application_date: date | None = None
    status: ApplicationStatus | None = None
    resume_id: str | None = Field(default=None, max_length=64)
    job_match_id: str | None = Field(default=None, max_length=64)
    interview_dates: list[InterviewDateEntry] | None = Field(default=None, max_length=20)
    notes: str | None = Field(default=None, max_length=8000)
    follow_up_date: date | None = None

    @field_validator("job_posting_url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return None
        cleaned = str(value).strip()
        if not cleaned.startswith(("http://", "https://")):
            raise ValueError("Job posting URL must start with http:// or https://")
        return cleaned


class JobApplicationResponse(BaseModel):
    id: str
    user_id: str
    company: str
    job_title: str
    job_description: str
    job_posting_url: str | None
    location: str
    employment_type: EmploymentType
    application_date: date | None
    status: ApplicationStatus
    resume_id: str | None
    job_match_id: str | None
    interview_dates: list[InterviewDateEntry]
    notes: str
    follow_up_date: date | None
    interview_session_id: str | None = None
    created_at: datetime
    updated_at: datetime


class JobApplicationListResponse(BaseModel):
    items: list[JobApplicationResponse]
    total: int
    page: int
    page_size: int
    disclaimer: str = JOB_APPLICATION_DISCLAIMER


class JobApplicationStatsResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    upcoming_interviews: list[dict]
    upcoming_follow_ups: list[dict]
    disclaimer: str = JOB_APPLICATION_DISCLAIMER


class StartApplicationPracticeRequest(BaseModel):
    resume_id: str | None = Field(default=None, max_length=64)
    question_count: int = Field(default=5, ge=3, le=10)
    voice_interview_enabled: bool = False


class StartApplicationPracticeResponse(BaseModel):
    application_id: str
    interview_session_id: str
    disclaimer: str = JOB_APPLICATION_DISCLAIMER
