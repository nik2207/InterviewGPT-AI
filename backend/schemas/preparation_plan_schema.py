from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

PlanStatus = Literal["active", "archived"]
PlanWorkflowStatus = Literal[
    "insufficient_data",
    "completed",
    "generation_failed",
    "validation_failed",
]
TaskType = Literal["learning", "practice_question", "exercise", "review"]

DAY_THEMES: dict[int, str] = {
    1: "Identify and prioritise gaps",
    2: "Revise important technical concepts",
    3: "Practise project explanations",
    4: "Practise behavioural questions",
    5: "Technical mock interview",
    6: "Focus on weakest areas",
    7: "Final mock interview and review",
}


class GeneratePreparationPlanRequest(BaseModel):
    resume_id: str = Field(..., min_length=1, max_length=64)
    job_match_id: str | None = Field(default=None, max_length=64)
    daily_study_minutes: int = Field(default=45, ge=15, le=240)
    archive_plan_id: str | None = Field(
        default=None,
        max_length=64,
        description="When set, archive this plan before creating a new one (regenerate flow).",
    )


class GeminiPlanDayPayload(BaseModel):
    day_number: int = Field(..., ge=1, le=7)
    learning_objective: str = Field(..., min_length=10, max_length=800)
    skills_to_practice: list[str] = Field(..., min_length=1, max_length=12)
    learning_activities: list[str] = Field(..., min_length=1, max_length=8)
    interview_questions: list[str] = Field(..., min_length=1, max_length=8)
    practical_exercise: str | None = Field(default=None, max_length=1500)
    estimated_duration_minutes: int = Field(..., ge=10, le=300)
    completion_criteria: str = Field(..., min_length=10, max_length=800)


class GeminiSevenDayPlanPayload(BaseModel):
    plan_summary: str = Field(..., min_length=20, max_length=2000)
    priority_gaps: list[str] = Field(..., min_length=1, max_length=15)
    days: list[GeminiPlanDayPayload] = Field(..., min_length=7, max_length=7)

    @field_validator("days")
    @classmethod
    def validate_day_numbers(cls, value: list[GeminiPlanDayPayload]) -> list[GeminiPlanDayPayload]:
        numbers = sorted(item.day_number for item in value)
        if numbers != list(range(1, 8)):
            raise ValueError("days must include day_number 1 through 7 exactly once")
        return value


class PreparationPlanTask(BaseModel):
    task_id: str = Field(..., min_length=3, max_length=40)
    title: str = Field(..., min_length=3, max_length=300)
    description: str = Field(..., max_length=2000)
    task_type: TaskType
    estimated_minutes: int = Field(..., ge=5, le=180)
    completed: bool = False
    completed_at: datetime | None = None


class PreparationPlanDay(BaseModel):
    day_number: int = Field(..., ge=1, le=7)
    relative_label: str
    scheduled_date: date
    theme: str
    learning_objective: str
    skills_to_practice: list[str]
    learning_activities: list[str]
    interview_questions: list[str]
    practical_exercise: str | None = None
    estimated_duration_minutes: int
    completion_criteria: str
    tasks: list[PreparationPlanTask] = Field(..., min_length=1)
    day_completed: bool = False


class PreparationPlanListItem(BaseModel):
    id: str
    resume_id: str
    job_match_id: str | None
    status: PlanStatus
    daily_study_minutes: int
    progress_percent: float
    created_at: datetime
    plan_start_date: date


class PreparationPlanListResponse(BaseModel):
    plans: list[PreparationPlanListItem]


class UpdatePlanTaskCompletionRequest(BaseModel):
    completed: bool


class PreparationPlanResponse(BaseModel):
    id: str
    user_id: str
    resume_id: str
    job_match_id: str | None
    status: PlanStatus
    daily_study_minutes: int
    model: str
    plan_start_date: date
    created_at: datetime
    updated_at: datetime
    plan_summary: str
    priority_gaps: list[str]
    days: list[PreparationPlanDay]
    progress_percent: float
    tasks_completed: int
    tasks_total: int
    today_day_number: int | None = None


class PreparationPlanEvidenceItem(BaseModel):
    source: Literal[
        "resume_analysis",
        "job_match",
        "interview_evaluation",
        "interview_summary",
    ]
    label: str = Field(..., max_length=200)
    observation: str = Field(..., max_length=1200)


class PreparationPlanEvidenceBundle(BaseModel):
    user_id: str
    resume_id: str
    job_match_id: str | None = None
    target_role: str = Field(default="Interview preparation", max_length=200)
    daily_study_minutes: int
    average_interview_score: float | None = None
    weakness_technical: list[str] = Field(default_factory=list, max_length=15)
    weakness_behavioral: list[str] = Field(default_factory=list, max_length=15)
    items: list[PreparationPlanEvidenceItem] = Field(..., min_length=1, max_length=50)
