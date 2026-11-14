from schemas.preparation_plan_schema import (
    PreparationPlanEvidenceBundle,
    PreparationPlanEvidenceItem,
)


def _truncate(text: str, limit: int = 900) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def _collect_weaknesses_from_sessions(sessions: list[dict]) -> tuple[list[str], list[str], float | None]:
    technical: list[str] = []
    behavioral: list[str] = []
    scores: list[float] = []

    for session in sessions:
        summary = session.get("summary") or {}
        avg = summary.get("average_score")
        if avg is not None:
            scores.append(float(avg))

        for answer in session.get("answers", []):
            if answer.get("evaluation_status") != "evaluated":
                continue
            question_id = answer.get("question_id")
            question = next(
                (q for q in session.get("questions", []) if q.get("id") == question_id),
                None,
            )
            category = (question or {}).get("category", "general").lower()
            evaluation = answer.get("evaluation") or {}
            dims = evaluation.get("dimension_scores") or {}

            gaps = list(evaluation.get("missing_concepts") or [])
            coach = evaluation.get("improvement_coach") or {}
            gaps.extend(coach.get("missing_important_points") or [])

            if dims.get("technical_correctness", 5) <= 3 or category == "technical":
                for item in gaps[:2]:
                    if item not in technical:
                        technical.append(_truncate(str(item), 200))
            if category == "behavioral" or dims.get("answer_structure", 5) <= 3:
                for item in gaps[:2]:
                    if item not in behavioral:
                        behavioral.append(_truncate(str(item), 200))
                star = coach.get("star_assessment")
                if isinstance(star, dict) and star.get("missing_star_elements"):
                    label = ", ".join(star["missing_star_elements"])
                    observation = f"Missing STAR elements: {label}"
                    if observation not in behavioral:
                        behavioral.append(observation)

    average = round(sum(scores) / len(scores), 1) if scores else None
    return technical[:12], behavioral[:12], average


def build_preparation_plan_evidence(
    *,
    user_id: str,
    resume_id: str,
    job_match_id: str | None,
    daily_study_minutes: int,
    resume_analysis: dict | None,
    job_match: dict | None,
    interview_sessions: list[dict],
) -> PreparationPlanEvidenceBundle | None:
    items: list[PreparationPlanEvidenceItem] = []
    target_role = "Interview preparation"

    if resume_analysis:
        analysis = resume_analysis.get("analysis") or {}
        target_role = (analysis.get("role_recommendations") or ["Interview preparation"])[0]
        items.append(
            PreparationPlanEvidenceItem(
                source="resume_analysis",
                label="Professional summary",
                observation=_truncate(analysis.get("professional_summary", "")),
            )
        )
        for skill in (analysis.get("skills") or [])[:8]:
            items.append(
                PreparationPlanEvidenceItem(
                    source="resume_analysis",
                    label="Resume skill",
                    observation=_truncate(str(skill)),
                )
            )
        for gap in (analysis.get("skill_gaps") or analysis.get("areas_to_improve") or [])[:5]:
            items.append(
                PreparationPlanEvidenceItem(
                    source="resume_analysis",
                    label="Resume gap",
                    observation=_truncate(str(gap)),
                )
            )

    if job_match:
        target_role = job_match.get("job_title") or target_role
        items.append(
            PreparationPlanEvidenceItem(
                source="job_match",
                label="Job match score",
                observation=f"{job_match.get('score', {}).get('match_score', 0)}% match",
            )
        )
        items.append(
            PreparationPlanEvidenceItem(
                source="job_match",
                label="Gap summary",
                observation=_truncate(job_match.get("gap_summary", "")),
            )
        )
        for alignment in (job_match.get("skill_alignments") or [])[:12]:
            if alignment.get("match_status") != "matched":
                items.append(
                    PreparationPlanEvidenceItem(
                        source="job_match",
                        label=f"Job skill ({alignment.get('requirement_type', 'req')})",
                        observation=_truncate(
                            f"{alignment.get('skill')}: {alignment.get('match_status')} — "
                            f"{alignment.get('gap_explanation', '')}"
                        ),
                    )
                )

    technical_weak, behavioral_weak, average_score = _collect_weaknesses_from_sessions(
        interview_sessions
    )

    for session in interview_sessions[:3]:
        summary = session.get("summary") or {}
        for area in (summary.get("focus_areas") or [])[:3]:
            items.append(
                PreparationPlanEvidenceItem(
                    source="interview_summary",
                    label=f"Focus area ({session.get('role', 'role')})",
                    observation=_truncate(str(area)),
                )
            )

    for weakness in technical_weak[:6]:
        items.append(
            PreparationPlanEvidenceItem(
                source="interview_evaluation",
                label="Technical weakness",
                observation=weakness,
            )
        )
    for weakness in behavioral_weak[:6]:
        items.append(
            PreparationPlanEvidenceItem(
                source="interview_evaluation",
                label="Behavioural weakness",
                observation=weakness,
            )
        )

    if not items:
        return None

    return PreparationPlanEvidenceBundle(
        user_id=user_id,
        resume_id=resume_id,
        job_match_id=job_match_id,
        target_role=str(target_role)[:200],
        daily_study_minutes=daily_study_minutes,
        average_interview_score=average_score,
        weakness_technical=technical_weak,
        weakness_behavioral=behavioral_weak,
        items=items[:50],
    )
