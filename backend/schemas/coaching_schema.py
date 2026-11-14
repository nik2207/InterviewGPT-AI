from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

WorkflowStatus = Literal[
    "insufficient_data",
    "completed",
    "generation_failed",
    "validation_failed",
]


class CoachingEvidenceItem(BaseModel):
    source: Literal["interview_session", "resume_analysis", "interview_history"]
    label: str = Field(..., max_length=200)
    observation: str = Field(..., max_length=1000)


class CoachingEvidenceBundle(BaseModel):
    user_id: str
    session_id: str
    role: str
    session_average_score: float | None = None
    items: list[CoachingEvidenceItem] = Field(..., min_length=1, max_length=40)


class GeminiCoachingPlanPayload(BaseModel):
    observed_strengths: list[str] = Field(..., min_length=1, max_length=10)
    observed_gaps: list[str] = Field(..., max_length=10)
    recommended_focus_areas: list[str] = Field(..., min_length=1, max_length=10)
    practice_suggestions: list[str] = Field(..., min_length=1, max_length=10)
    summary: str = Field(..., min_length=20, max_length=2000)


class CoachingPlanResponse(BaseModel):
    session_id: str
    status: WorkflowStatus
    generated_at: datetime
    evidence_count: int
    plan: GeminiCoachingPlanPayload | None = None
    message: str | None = None
    disclaimer: str = (
        "Recommendations are based only on saved resume analysis and interview "
        "results. They are not guarantees of future performance."
    )
