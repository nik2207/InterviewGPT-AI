import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from schemas.interview_schema import (
    AnswerDimensionScores,
    GeminiAnswerEvaluationPayload,
    GeminiAnswerImprovementCoach,
)
from services.gemini_answer_evaluation_service import (
    AnswerEvaluationError,
    evaluate_answer_text,
)


def _valid_payload_dict() -> dict:
    return {
        "dimension_scores": {
            "technical_correctness": 4,
            "relevance": 4,
            "completeness": 3,
            "answer_structure": 4,
        },
        "strengths": ["Accurate core idea"],
        "missing_concepts": ["Scalability"],
        "improvement_suggestions": ["Mention trade-offs"],
        "feedback_summary": "Good technical start with room for depth.",
        "improvement_coach": {
            "missing_important_points": ["Scalability limits"],
            "incorrect_or_unclear": [],
            "relevance_to_question": "Mostly on topic.",
            "improved_example_answer": "Explain the algorithm, then note time complexity and a scaling approach.",
            "why_example_is_stronger": "Adds structure and depth.",
            "concepts_to_revise": ["Big-O"],
            "follow_up_practice_question": "How would you shard this service?",
            "action_to_take": "Revise complexity analysis for one past project.",
            "star_assessment": None,
        },
    }


@patch(
    "services.gemini_answer_evaluation_service.call_with_transient_retries",
    side_effect=lambda fn, **kwargs: fn(),
)
@patch("services.gemini_answer_evaluation_service.build_gemini_client")
@patch("services.gemini_answer_evaluation_service.get_gemini_api_key", return_value="key")
@patch("services.gemini_answer_evaluation_service.get_gemini_model", return_value="gemini-test")
def test_evaluate_answer_includes_improvement_coach(
    mock_model, mock_key, mock_client, _retry
):
    response = MagicMock()
    response.text = json.dumps(_valid_payload_dict())
    mock_client.return_value.models.generate_content.return_value = response

    result = evaluate_answer_text(
        role="Engineer",
        question="Explain caching?",
        category="technical",
        evaluates="System design",
        answer_text="Caching stores hot data in memory.",
    )
    assert result.improvement_coach is not None
    assert result.improvement_coach.follow_up_practice_question
    assert result.improvement_coach.what_went_well == result.strengths


@patch(
    "services.gemini_answer_evaluation_service.call_with_transient_retries",
    side_effect=lambda fn, **kwargs: fn(),
)
@patch("services.gemini_answer_evaluation_service.build_gemini_client")
@patch("services.gemini_answer_evaluation_service.get_gemini_api_key", return_value="key")
@patch("services.gemini_answer_evaluation_service.get_gemini_model", return_value="gemini-test")
def test_evaluate_answer_malformed_json(mock_model, mock_key, mock_client, _retry):
    response = MagicMock()
    response.text = '{"dimension_scores": {}}'
    mock_client.return_value.models.generate_content.return_value = response

    with pytest.raises(AnswerEvaluationError):
        evaluate_answer_text(
            role="Engineer",
            question="Tell me about a conflict?",
            category="behavioral",
            evaluates="STAR",
            answer_text="",
        )


def test_gemini_payload_requires_coach_section():
    with pytest.raises(ValidationError):
        GeminiAnswerEvaluationPayload.model_validate(
            {
                "dimension_scores": AnswerDimensionScores(
                    technical_correctness=1,
                    relevance=1,
                    completeness=1,
                    answer_structure=1,
                ),
                "strengths": ["Tried"],
                "missing_concepts": [],
                "improvement_suggestions": ["Add detail"],
                "feedback_summary": "Too brief to assess fully.",
            }
        )


def test_behavioural_star_schema_optional():
    payload = GeminiAnswerImprovementCoach(
        missing_important_points=["No measurable result"],
        incorrect_or_unclear=[],
        relevance_to_question="Partial STAR",
        improved_example_answer="Situation: … Task: … Action: … Result: …",
        why_example_is_stronger="Uses STAR without inventing employers.",
        concepts_to_revise=[],
        follow_up_practice_question="Describe another leadership moment?",
        action_to_take="Add one metric to your result sentence.",
        star_assessment={
            "uses_star": False,
            "missing_star_elements": ["result"],
            "specificity_suggestions": ["Name the timeframe"],
        },
    )
    assert payload.star_assessment is not None
