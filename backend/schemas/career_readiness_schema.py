from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

READINESS_SCORING_RULES = (
    "Career readiness is computed deterministically from stored data only (no AI score). "
    "Component scores use: job match % for alignment; interview dimension averages "
    "(1–5 scaled to 0–100) for technical, relevance, completeness, structure; "
    "mean session overall_score for interview performance; preparation plan task "
    "completion % when a plan exists. Overall readiness = weighted mean of available "
    "components with weights renormalized when some are missing: alignment 25%, "
    "technical 20%, relevance 15%, completeness 15%, structure 10%, "
    "interview performance 10%, preparation progress 5%. "
    "If no interview evaluations exist, overall readiness is unavailable "
    "(Not enough practice data). Speech metrics are descriptive timing/word-use only."
)

SPEECH_DISCLAIMER = (
    "Speech timing and filler-word counts are descriptive metrics only. "
    "They are not measures of confidence, personality, or psychological state."
)


class GenerateCareerReadinessRequest(BaseModel):
    resume_id: str = Field(..., min_length=1, max_length=64)
    job_match_id: str | None = Field(default=None, max_length=64)


class DataCoverageItem(BaseModel):
    source: str
    available: bool
    detail: str
    last_updated: datetime | None = None


class DataCoverageSummary(BaseModel):
    items: list[DataCoverageItem]
    summary: str


class OverallReadinessIndicator(BaseModel):
    score: float | None = Field(default=None, ge=0, le=100)
    status: Literal["available", "insufficient_data"]
    message: str


class ComponentScoreSection(BaseModel):
    score: float | None = Field(default=None, ge=0, le=100)
    status: Literal["available", "insufficient_data"]
    detail: str
    sample_size: int = 0


class InterviewTrendPoint(BaseModel):
    session_id: str
    role: str
    completed_at: datetime
    overall_score: float | None


class PreparationPlanSummarySection(BaseModel):
    plan_id: str
    status: str
    progress_percent: float
    tasks_completed: int
    tasks_total: int
    last_updated: datetime


class CommunicationIndicatorsSection(BaseModel):
    status: Literal["available", "insufficient_data"]
    speech_answer_count: int = 0
    average_words_per_minute: float | None = None
    average_filler_words: float | None = None
    disclaimer: str = SPEECH_DISCLAIMER
    detail: str = ""


class CareerReadinessReportListItem(BaseModel):
    id: str
    resume_id: str
    job_match_id: str | None
    target_role: str
    overall_score: float | None
    overall_status: Literal["available", "insufficient_data"]
    generated_at: datetime


class CareerReadinessReportListResponse(BaseModel):
    reports: list[CareerReadinessReportListItem]


class CareerReadinessReportResponse(BaseModel):
    id: str
    user_id: str
    resume_id: str
    job_match_id: str | None
    target_role: str
    generated_at: datetime
    data_coverage: DataCoverageSummary
    overall_readiness: OverallReadinessIndicator
    resume_job_alignment: ComponentScoreSection
    technical_knowledge: ComponentScoreSection
    answer_relevance: ComponentScoreSection
    answer_completeness: ComponentScoreSection
    answer_structure: ComponentScoreSection
    communication_indicators: CommunicationIndicatorsSection
    strongest_skills: list[str]
    skills_requiring_improvement: list[str]
    interview_performance_trends: list[InterviewTrendPoint]
    preparation_plan: PreparationPlanSummarySection | None
    recommended_next_actions: list[str] = Field(..., min_length=1, max_length=12)
    scoring_rules: str = READINESS_SCORING_RULES
