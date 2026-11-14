from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ResumeBuilderTemplate = Literal["classic", "professional", "compact"]

REORDERABLE_SECTION_KEYS = [
    "professional_summary",
    "education",
    "work_experience",
    "internships",
    "technical_skills",
    "projects",
    "certifications",
    "achievements",
    "languages",
]

RESUME_BUILDER_ATS_DISCLAIMER = (
    "This builder helps produce readable, text-friendly resumes. It does not "
    "guarantee ATS compatibility or a specific ATS score. Always verify content "
    "accuracy before applying."
)

RESUME_AI_DISCLAIMER = (
    "AI suggestions rephrase content you provide. They do not add employers, "
    "degrees, certifications, metrics, or results unless you supplied them. "
    "Confirm changes before saving."
)


class PersonalInfoSection(BaseModel):
    full_name: str = Field(default="", max_length=120)
    email: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=40)
    location: str = Field(default="", max_length=120)
    linkedin: str = Field(default="", max_length=300)
    github: str = Field(default="", max_length=300)
    portfolio: str = Field(default="", max_length=300)


class EducationEntry(BaseModel):
    id: str = Field(..., min_length=1, max_length=32)
    institution: str = Field(default="", max_length=200)
    degree: str = Field(default="", max_length=200)
    field_of_study: str = Field(default="", max_length=200)
    start_date: str = Field(default="", max_length=40)
    end_date: str = Field(default="", max_length=40)
    details: list[str] = Field(default_factory=list, max_length=12)


class ExperienceEntry(BaseModel):
    id: str = Field(..., min_length=1, max_length=32)
    company: str = Field(default="", max_length=200)
    title: str = Field(default="", max_length=200)
    location: str = Field(default="", max_length=120)
    start_date: str = Field(default="", max_length=40)
    end_date: str = Field(default="", max_length=40)
    bullets: list[str] = Field(default_factory=list, max_length=20)


class ProjectEntry(BaseModel):
    id: str = Field(..., min_length=1, max_length=32)
    name: str = Field(default="", max_length=200)
    url: str = Field(default="", max_length=300)
    technologies: list[str] = Field(default_factory=list, max_length=20)
    description: str = Field(default="", max_length=2000)
    bullets: list[str] = Field(default_factory=list, max_length=15)


class CertificationEntry(BaseModel):
    id: str = Field(..., min_length=1, max_length=32)
    name: str = Field(default="", max_length=200)
    issuer: str = Field(default="", max_length=200)
    date: str = Field(default="", max_length=40)


class LanguageEntry(BaseModel):
    id: str = Field(..., min_length=1, max_length=32)
    language: str = Field(default="", max_length=80)
    proficiency: str = Field(default="", max_length=80)


class ResumeBuilderContent(BaseModel):
    personal_info: PersonalInfoSection = Field(default_factory=PersonalInfoSection)
    professional_summary: str = Field(default="", max_length=3000)
    education: list[EducationEntry] = Field(default_factory=list, max_length=15)
    work_experience: list[ExperienceEntry] = Field(default_factory=list, max_length=20)
    internships: list[ExperienceEntry] = Field(default_factory=list, max_length=15)
    technical_skills: list[str] = Field(default_factory=list, max_length=60)
    projects: list[ProjectEntry] = Field(default_factory=list, max_length=20)
    certifications: list[CertificationEntry] = Field(default_factory=list, max_length=20)
    achievements: list[str] = Field(default_factory=list, max_length=30)
    languages: list[LanguageEntry] = Field(default_factory=list, max_length=20)


class ResumeBuilderVersion(BaseModel):
    version_number: int = Field(..., ge=1)
    label: str = Field(default="Draft save", max_length=120)
    content: ResumeBuilderContent
    created_at: datetime


class CreateResumeBuilderRequest(BaseModel):
    title: str = Field(default="My resume", min_length=1, max_length=120)
    template: ResumeBuilderTemplate = "classic"
    source_upload_resume_id: str | None = Field(default=None, max_length=64)


class UpdateResumeBuilderRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    template: ResumeBuilderTemplate | None = None
    section_order: list[str] | None = Field(default=None, max_length=20)
    content: ResumeBuilderContent | None = None


class SaveResumeBuilderVersionRequest(BaseModel):
    label: str = Field(default="Manual save", min_length=1, max_length=120)


class ResumeBuilderListItem(BaseModel):
    id: str
    title: str
    template: ResumeBuilderTemplate
    updated_at: datetime
    version_count: int
    source_upload_resume_id: str | None = None


class ResumeBuilderListResponse(BaseModel):
    items: list[ResumeBuilderListItem]
    disclaimer: str = RESUME_BUILDER_ATS_DISCLAIMER


class ResumeBuilderDetailResponse(BaseModel):
    id: str
    user_id: str
    title: str
    template: ResumeBuilderTemplate
    section_order: list[str]
    content: ResumeBuilderContent
    versions: list[ResumeBuilderVersion]
    source_upload_resume_id: str | None = None
    disclaimer: str = RESUME_BUILDER_ATS_DISCLAIMER
    created_at: datetime
    updated_at: datetime


ResumeAiFeature = Literal[
    "improve_summary",
    "improve_bullets",
    "improve_project",
    "missing_info",
    "job_keywords",
    "ats_formatting",
]


class ImproveBulletsRequest(BaseModel):
    experience_id: str = Field(..., min_length=1, max_length=32)
    section: Literal["work_experience", "internships"] = "work_experience"


class ImproveProjectRequest(BaseModel):
    project_id: str = Field(..., min_length=1, max_length=32)


class JobKeywordsRequest(BaseModel):
    job_description: str = Field(..., min_length=80, max_length=15000)


class ResumeAiProposalResponse(BaseModel):
    feature: ResumeAiFeature
    original_text: str
    improved_text: str
    comparison_notes: str
    missing_information: list[str] = Field(default_factory=list, max_length=15)
    keyword_suggestions: list[str] = Field(default_factory=list, max_length=30)
    ats_formatting_notes: list[str] = Field(default_factory=list, max_length=15)
    requires_user_confirmation: bool = True
    disclaimer: str = RESUME_AI_DISCLAIMER
