from datetime import date

from schemas.preparation_plan_schema import GeminiPlanDayPayload
from services.preparation_plan_service import (
    _build_tasks,
    _gemini_days_to_stored,
    _progress,
)


def _sample_day(number: int) -> GeminiPlanDayPayload:
    return GeminiPlanDayPayload(
        day_number=number,
        learning_objective=f"Objective for day {number}",
        skills_to_practice=["Python"],
        learning_activities=["Read docs", "Take notes"],
        interview_questions=["Explain REST?", "Describe a bug you fixed?"],
        practical_exercise="Refactor a small handler",
        estimated_duration_minutes=45,
        completion_criteria="Can explain concepts aloud",
    )


def test_build_tasks_includes_all_activity_types():
    tasks = _build_tasks(_sample_day(1))
    types = {t.task_type for t in tasks}
    assert "learning" in types
    assert "practice_question" in types
    assert "exercise" in types
    assert "review" in types


def test_progress_calculation():
    days = [
        {
            "tasks": [
                {"completed": True},
                {"completed": False},
            ]
        },
        {"tasks": [{"completed": True}]},
    ]
    percent, completed, total = _progress(days)
    assert total == 3
    assert completed == 2
    assert percent == 66.7


def test_gemini_days_to_stored_has_seven_days():
    days = [_sample_day(n) for n in range(1, 8)]
    stored = _gemini_days_to_stored(days, date(2026, 1, 1))
    assert len(stored) == 7
    assert stored[0]["theme"].startswith("Identify")
