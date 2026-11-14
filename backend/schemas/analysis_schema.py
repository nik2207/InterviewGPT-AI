from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

DifficultyLevel = Literal["beginner", "intermediate", "advanced"]
AnalysisStatus = Literal["completed", "failed"]


class InterviewQuestionSchema(BaseModel):
    question: str = Field(..., min_length=5, max_length=500)
    category: str = Field(..., min_length=2, max_length=80)
    difficulty: DifficultyLevel
    relevance: str = Field(
        ...,
        min_length=3,
        max_length=300,
        description="Resume skill, project, or experience this question relates to",
    )
    evaluates: str = Field(
        ...,
        min_length=3,
        max_length=300,
        description="What the interviewer is assessing",
    )


class ResumeAnalysisPayloadSchema(BaseModel):
    professional_summary: str = Field(..., min_length=10, max_length=2000)
    skills: list[str] = Field(..., min_length=1, max_length=40)
    experience_analysis: str = Field(..., min_length=10, max_length=4000)
    projects_analysis: str = Field(..., min_length=10, max_length=4000)
    strengths: list[str] = Field(..., min_length=1, max_length=20)
    areas_to_improve: list[str] = Field(..., min_length=1, max_length=20)
    missing_or_unclear_information: list[str] = Field(..., max_length=20)
    ats_readability_suggestions: list[str] = Field(..., min_length=1, max_length=15)
    role_recommendations: list[str] = Field(..., min_length=1, max_length=15)
    skill_gaps: list[str] = Field(..., max_length=20)
    interview_questions: list[InterviewQuestionSchema] = Field(
        ...,
        min_length=8,
        max_length=20,
    )

    @field_validator("skills", "strengths", "areas_to_improve", mode="before")
    @classmethod
    def strip_list_items(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and str(item).strip()]


class GeminiResumeAnalysisResult(BaseModel):
    analysis: ResumeAnalysisPayloadSchema


class InterviewQuestionResponse(BaseModel):
    question: str
    category: str
    difficulty: DifficultyLevel
    relevance: str
    evaluates: str


class ResumeAnalysisSectionsResponse(BaseModel):
    professional_summary: str
    skills: list[str]
    experience_analysis: str
    projects_analysis: str
    strengths: list[str]
    areas_to_improve: list[str]
    missing_or_unclear_information: list[str]
    ats_readability_suggestions: list[str]
    role_recommendations: list[str]
    skill_gaps: list[str]


class ResumeAnalysisResponse(BaseModel):
    id: str
    resume_id: str
    user_id: str
    status: AnalysisStatus
    model: str
    created_at: datetime
    updated_at: datetime
    analysis: ResumeAnalysisSectionsResponse
    interview_questions: list[InterviewQuestionResponse]
    cached: bool = False


class AnalyzeResumeQuery(BaseModel):
    refresh: bool = False
