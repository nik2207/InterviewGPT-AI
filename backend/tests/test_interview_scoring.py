from schemas.interview_schema import AnswerDimensionScores, compute_overall_score


def test_compute_overall_score_weighted():
    scores = AnswerDimensionScores(
        technical_correctness=5,
        relevance=4,
        completeness=3,
        answer_structure=2,
    )
    # (5/5*0.35 + 4/5*0.25 + 3/5*0.25 + 2/5*0.15) * 100
    expected = round((0.35 + 0.2 + 0.15 + 0.06) * 100, 1)
    assert compute_overall_score(scores) == expected
