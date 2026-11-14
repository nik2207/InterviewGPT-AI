from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from schemas.interview_schema import DifficultyLevel

PrepCategory = Literal["technical", "hr", "coding", "behavioural"]
ExperienceLevel = Literal["junior", "mid", "senior"]
ContentSourceType = Literal[
    "ai_generated_practice",
    "catalogue_public",
    "user_provided",
]

COMPANY_PREP_DISCLAIMER = (
    "Practice questions are for preparation only. They are not actual, leaked, or "
    "guaranteed questions from any company interview. Verified public information is "
    "labelled separately from AI-generated practice content."
)

AI_PRACTICE_QUESTION_DISCLAIMER = (
    "AI-generated practice question for interview preparation. Not from a real interview."
)


class CompanyPublicSource(BaseModel):
    label: str = Field(..., min_length=2, max_length=120)
    url: str = Field(..., min_length=8, max_length=500)


class CompanyPrepMaterialItem(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    source_type: ContentSourceType
    source_url: str | None = Field(default=None, max_length=500)
    summary: str = Field(..., min_length=10, max_length=2000)


class CompanyCatalogueEntry(BaseModel):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    industry: str
    headquarters: str
    public_profile_summary: str
    verified_public_sources: list[CompanyPublicSource] = Field(default_factory=list)
    public_prep_topics: list[str] = Field(default_factory=list)
    prep_material: list[CompanyPrepMaterialItem] = Field(default_factory=list)


class CompanyCatalogueListResponse(BaseModel):
    disclaimer: str
    companies: list[CompanyCatalogueEntry]


class CompanyPrepQuestion(BaseModel):
    id: str
    question: str = Field(..., min_length=5, max_length=500)
    prep_category: PrepCategory
    difficulty: DifficultyLevel
    relevance: str = Field(..., max_length=300)
    evaluates: str = Field(..., max_length=300)
    source_type: ContentSourceType
    source_label: str = Field(..., min_length=5, max_length=300)
    disclaimer: str = AI_PRACTICE_QUESTION_DISCLAIMER


class ChecklistItem(BaseModel):
    id: str
    label: str = Field(..., min_length=3, max_length=300)
    prep_category: PrepCategory | Literal["general"] = "general"
    completed: bool = False
    source_type: ContentSourceType
    source_label: str = Field(..., min_length=3, max_length=300)


class CreateCompanyPrepRequest(BaseModel):
    company_id: str = Field(..., min_length=2, max_length=64)
    job_role: str = Field(..., min_length=2, max_length=120)
    experience_level: ExperienceLevel
    categories: list[PrepCategory] = Field(..., min_length=1, max_length=4)
    user_notes: str | None = Field(default=None, max_length=2000)

    @field_validator("categories")
    @classmethod
    def unique_categories(cls, value: list[PrepCategory]) -> list[PrepCategory]:
        seen: set[str] = set()
        ordered: list[PrepCategory] = []
        for item in value:
            if item not in seen:
                seen.add(item)
                ordered.append(item)
        return ordered


class UpdateCompanyPrepChecklistRequest(BaseModel):
    items: list[ChecklistItem] = Field(..., min_length=1, max_length=40)


class GeminiCompanyPrepQuestionInput(BaseModel):
    question: str = Field(..., min_length=5, max_length=500)
    prep_category: PrepCategory
    difficulty: DifficultyLevel
    relevance: str = Field(..., max_length=300)
    evaluates: str = Field(..., max_length=300)
    source_label: str = Field(..., min_length=5, max_length=300)


class GeminiCompanyPrepChecklistInput(BaseModel):
    label: str = Field(..., min_length=3, max_length=300)
    prep_category: PrepCategory | Literal["general"] = "general"
    source_type: ContentSourceType = "ai_generated_practice"
    source_label: str = Field(..., min_length=3, max_length=300)


class GeminiCompanyPrepPayload(BaseModel):
    practice_questions: list[GeminiCompanyPrepQuestionInput] = Field(
        ..., min_length=4, max_length=16
    )
    checklist_items: list[GeminiCompanyPrepChecklistInput] = Field(
        ..., min_length=4, max_length=20
    )


class CompanyPrepListItem(BaseModel):
    id: str
    company_id: str
    company_name: str
    job_role: str
    experience_level: ExperienceLevel
    categories: list[PrepCategory]
    question_count: int
    created_at: datetime
    interview_session_id: str | None = None


class CompanyPrepListResponse(BaseModel):
    preparations: list[CompanyPrepListItem]
    disclaimer: str = COMPANY_PREP_DISCLAIMER


class CompanyPrepDetailResponse(BaseModel):
    id: str
    user_id: str
    company: CompanyCatalogueEntry
    job_role: str
    experience_level: ExperienceLevel
    categories: list[PrepCategory]
    user_notes: str | None = None
    questions: list[CompanyPrepQuestion]
    checklist: list[ChecklistItem]
    interview_session_id: str | None = None
    disclaimer: str = COMPANY_PREP_DISCLAIMER
    created_at: datetime
    updated_at: datetime


class StartCompanyPrepInterviewRequest(BaseModel):
    resume_id: str | None = Field(default=None, max_length=64)
    question_count: int = Field(default=5, ge=3, le=15)
    voice_interview_enabled: bool = False


class StartCompanyPrepInterviewResponse(BaseModel):
    preparation_id: str
    interview_session_id: str
    disclaimer: str = COMPANY_PREP_DISCLAIMER
