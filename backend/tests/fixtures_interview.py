from schemas.interview_schema import (
    AnswerDimensionScores,
    AnswerEvaluationResponse,
    AnswerImprovementCoach,
)


def sample_evaluation(score: int = 4) -> AnswerEvaluationResponse:
    dimensions = AnswerDimensionScores(
        technical_correctness=score,
        relevance=score,
        completeness=score,
        answer_structure=score,
    )
    from schemas.interview_schema import compute_overall_score

    return AnswerEvaluationResponse(
        dimension_scores=dimensions,
        strengths=["Clear explanation"],
        missing_concepts=["Edge case handling"],
        improvement_suggestions=["Add concrete metrics"],
        feedback_summary="Solid answer with room to add more depth.",
        overall_score=compute_overall_score(dimensions),
        improvement_coach=AnswerImprovementCoach(
            what_went_well=["Clear explanation"],
            missing_important_points=["Edge case handling"],
            incorrect_or_unclear=[],
            relevance_to_question="The answer addresses the core topic.",
            improved_example_answer="A stronger answer would add a concrete metric and trade-off.",
            why_example_is_stronger="It combines clarity with measurable impact.",
            concepts_to_revise=["Error handling"],
            follow_up_practice_question="How would you handle a failure in production?",
            action_to_take="Add one metric from your real experience to your next draft.",
        ),
    )


def custom_questions_payload(count: int = 3) -> list[dict]:
    return [
        {
            "question": f"Custom interview question {index}?",
            "category": "technical",
            "difficulty": "intermediate",
            "relevance": "Python",
            "evaluates": "Technical depth",
        }
        for index in range(1, count + 1)
    ]
