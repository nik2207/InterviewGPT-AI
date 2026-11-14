from schemas.job_match_schema import SkillAlignmentItem
from services.job_match_score_service import compute_job_match_score


def test_compute_match_score_weighted():
    alignments = [
        SkillAlignmentItem(
            skill="Python",
            requirement_type="required",
            match_status="matched",
            resume_evidence="Built APIs in Python",
            gap_explanation="",
        ),
        SkillAlignmentItem(
            skill="Kubernetes",
            requirement_type="required",
            match_status="partial",
            resume_evidence="Docker experience",
            gap_explanation="K8s not explicit",
        ),
        SkillAlignmentItem(
            skill="GraphQL",
            requirement_type="preferred",
            match_status="not_evidenced",
            resume_evidence="",
            gap_explanation="Not on resume",
        ),
    ]
    score = compute_job_match_score(alignments)
    assert score.required_skill_count == 2
    assert score.required_matched == 1
    assert score.required_partial == 1
    assert score.match_score == 52.5
