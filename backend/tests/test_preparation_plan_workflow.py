from unittest.mock import patch

from schemas.preparation_plan_schema import PreparationPlanEvidenceBundle, PreparationPlanEvidenceItem
from workflows.preparation_plan_graph import run_preparation_plan_workflow


def _evidence() -> PreparationPlanEvidenceBundle:
    return PreparationPlanEvidenceBundle(
        user_id="u1",
        resume_id="r1",
        daily_study_minutes=45,
        items=[
            PreparationPlanEvidenceItem(
                source="resume_analysis",
                label="Skill",
                observation="Python",
            )
        ],
    )


def test_workflow_insufficient_data():
    result = run_preparation_plan_workflow(None)
    assert result["status"] == "insufficient_data"


@patch("workflows.preparation_plan_graph.generate_seven_day_plan")
def test_workflow_success(mock_generate):
    from schemas.preparation_plan_schema import GeminiPlanDayPayload, GeminiSevenDayPlanPayload

    mock_generate.return_value = GeminiSevenDayPlanPayload(
        plan_summary="A personalised week focused on your documented gaps.",
        priority_gaps=["Gap"],
        days=[
            GeminiPlanDayPayload(
                day_number=n,
                learning_objective="Revise core concepts from evidence",
                skills_to_practice=["s"],
                learning_activities=["a"],
                interview_questions=["q"],
                practical_exercise=None,
                estimated_duration_minutes=45,
                completion_criteria="All practice items completed",
            )
            for n in range(1, 8)
        ],
    )
    result = run_preparation_plan_workflow(_evidence())
    assert result["status"] == "completed"
    assert result["plan"] is not None
