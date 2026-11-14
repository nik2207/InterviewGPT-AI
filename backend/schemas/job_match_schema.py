from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from schemas.analysis_schema import InterviewQuestionResponse, InterviewQuestionSchema

MatchStatus = Literal["matched", "partial", "not_evidenced"]
RequirementType = Literal["required", "preferred"]
JobMatchStatus = Literal["completed", "failed"]

MATCH_SCORE_DESCRIPTION = (
    "Match score (0–100) is computed server-side from skill alignment: "
    "required skills count 70% of the score, preferred skills 30%. "
    "Each skill contributes 1.0 if matched, 0.5 if partially matched, "
    "0 if not evidenced on the resume. Gemini assigns alignment status; "
    "the numeric score is derived from those labels for transparency."
)


class CreateJobMatchRequest(BaseModel):
    resume_id: str = Field(..., min_length=1, max_length=64)
    job_description: str = Field(..., min_length=80, max_length=20000)
    job_title: str | None = Field(default=None, max_length=200)


class SkillAlignmentItem(BaseModel):
    skill: str = Field(..., min_length=1, max_length=200)
    requirement_type: RequirementType
    match_status: MatchStatus
    resume_evidence: str = Field(
        ...,
        min_length=0,
        max_length=800,
        description="Quote or paraphrase from resume/analysis only; empty if not evidenced",
    )
    gap_explanation: str = Field(..., min_length=0, max_length=500)


class JobMatchScoreBreakdown(BaseModel):
    required_skill_count: int = Field(..., ge=0)
    required_matched: int = Field(..., ge=0)
    required_partial: int = Field(..., ge=0)
    required_not_evidenced: int = Field(..., ge=0)
    preferred_skill_count: int = Field(..., ge=0)
    preferred_matched: int = Field(..., ge=0)
    preferred_partial: int = Field(..., ge=0)
    preferred_not_evidenced: int = Field(..., ge=0)
    match_score: float = Field(..., ge=0, le=100)
    score_explanation: str = Field(..., min_length=10, max_length=1500)
    scoring_rules: str = MATCH_SCORE_DESCRIPTION


class GeminiJobMatchPayload(BaseModel):
    job_title_inferred: str = Field(..., min_length=2, max_length=200)
    required_skills: list[str] = Field(..., min_length=1, max_length=40)
    preferred_skills: list[str] = Field(default_factory=list, max_length=40)
    skill_alignments: list[SkillAlignmentItem] = Field(..., min_length=1, max_length=60)
    gap_summary: str = Field(..., min_length=10, max_length=2000)
    strengths_for_role: list[str] = Field(..., min_length=1, max_length=15)
    interview_questions: list[InterviewQuestionSchema] = Field(
        ...,
        min_length=3,
        max_length=12,
    )

    @field_validator("required_skills", "preferred_skills", mode="before")
    @classmethod
    def strip_skills(cls, value: list[str]) -> list[str]:
        return [str(item).strip() for item in value if item and str(item).strip()]


class JobMatchListItem(BaseModel):
    id: str
    resume_id: str
    job_title: str
    match_score: float
    status: JobMatchStatus
    created_at: datetime


class JobMatchListResponse(BaseModel):
    matches: list[JobMatchListItem]


class JobMatchResponse(BaseModel):
    id: str
    user_id: str
    resume_id: str
    job_title: str
    status: JobMatchStatus
    model: str
    created_at: datetime
    updated_at: datetime
    job_description_excerpt: str
    required_skills: list[str]
    preferred_skills: list[str]
    skill_alignments: list[SkillAlignmentItem]
    score: JobMatchScoreBreakdown
    gap_summary: str
    strengths_for_role: list[str]
    interview_questions: list[InterviewQuestionResponse]
    error_message: str | None = None
