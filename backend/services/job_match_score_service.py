from schemas.job_match_schema import JobMatchScoreBreakdown, MATCH_SCORE_DESCRIPTION, SkillAlignmentItem


def _count_alignments(items: list[SkillAlignmentItem]) -> tuple[int, int, int, int]:
    matched = partial = missing = 0
    for item in items:
        if item.match_status == "matched":
            matched += 1
        elif item.match_status == "partial":
            partial += 1
        else:
            missing += 1
    return len(items), matched, partial, missing


def _weighted_points(matched: int, partial: int) -> float:
    return float(matched) + 0.5 * float(partial)


def compute_job_match_score(
    alignments: list[SkillAlignmentItem],
) -> JobMatchScoreBreakdown:
    required = [a for a in alignments if a.requirement_type == "required"]
    preferred = [a for a in alignments if a.requirement_type == "preferred"]

    req_total, req_m, req_p, req_n = _count_alignments(required)
    pref_total, pref_m, pref_p, pref_n = _count_alignments(preferred)

    req_points = _weighted_points(req_m, req_p)
    pref_points = _weighted_points(pref_m, pref_p)

    if req_total == 0 and pref_total == 0:
        return JobMatchScoreBreakdown(
            required_skill_count=0,
            required_matched=0,
            required_partial=0,
            required_not_evidenced=0,
            preferred_skill_count=0,
            preferred_matched=0,
            preferred_partial=0,
            preferred_not_evidenced=0,
            match_score=0.0,
            score_explanation="No skills were extracted for comparison.",
            scoring_rules=MATCH_SCORE_DESCRIPTION,
        )

    if req_total and pref_total:
        req_ratio = req_points / req_total if req_total else 0.0
        pref_ratio = pref_points / pref_total if pref_total else 0.0
        match_score = round((req_ratio * 0.7 + pref_ratio * 0.3) * 100.0, 1)
        explanation = (
            f"Required skills: {req_m} matched, {req_p} partial, {req_n} not evidenced "
            f"({req_points:.1f}/{req_total} weighted points). "
            f"Preferred skills: {pref_m} matched, {pref_p} partial, {pref_n} not evidenced "
            f"({pref_points:.1f}/{pref_total} weighted points). "
            "Overall = 70% required ratio + 30% preferred ratio."
        )
    elif req_total:
        req_ratio = req_points / req_total
        match_score = round(req_ratio * 100.0, 1)
        explanation = (
            f"Required skills only: {req_m} matched, {req_p} partial, {req_n} not evidenced "
            f"({req_points:.1f}/{req_total} weighted points)."
        )
    else:
        pref_ratio = pref_points / pref_total
        match_score = round(pref_ratio * 100.0, 1)
        explanation = (
            f"Preferred skills only: {pref_m} matched, {pref_p} partial, {pref_n} not evidenced "
            f"({pref_points:.1f}/{pref_total} weighted points)."
        )

    return JobMatchScoreBreakdown(
        required_skill_count=req_total,
        required_matched=req_m,
        required_partial=req_p,
        required_not_evidenced=req_n,
        preferred_skill_count=pref_total,
        preferred_matched=pref_m,
        preferred_partial=pref_p,
        preferred_not_evidenced=pref_n,
        match_score=match_score,
        score_explanation=explanation,
        scoring_rules=MATCH_SCORE_DESCRIPTION,
    )
