from services.career_readiness_scoring import (
    collect_dimension_scores,
    compute_overall_readiness,
    dimension_to_percent,
)


def test_overall_requires_interview_data():
    result = compute_overall_readiness(
        alignment=80.0,
        technical=None,
        relevance=None,
        completeness=None,
        structure=None,
        interview_performance=None,
        preparation=None,
    )
    assert result.status == "insufficient_data"
    assert result.score is None


def test_overall_weighted_with_interviews():
    result = compute_overall_readiness(
        alignment=60.0,
        technical=80.0,
        relevance=70.0,
        completeness=75.0,
        structure=65.0,
        interview_performance=72.0,
        preparation=40.0,
    )
    assert result.status == "available"
    assert result.score is not None
    assert 60 <= result.score <= 85


def test_collect_dimensions_from_session():
    sessions = [
        {
            "answers": [
                {
                    "evaluation_status": "evaluated",
                    "evaluation": {
                        "dimension_scores": {
                            "technical_correctness": 4,
                            "relevance": 3,
                            "completeness": 4,
                            "answer_structure": 5,
                        }
                    },
                }
            ]
        }
    ]
    dims = collect_dimension_scores(sessions)
    assert dimension_to_percent(dims["technical_correctness"]) == 80.0
