from schemas.coaching_schema import CoachingEvidenceBundle, CoachingEvidenceItem


def _truncate(text: str, limit: int = 900) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def build_evidence_bundle(
    *,
    user_id: str,
    session_id: str,
    session: dict,
    resume_analysis: dict | None,
    history_sessions: list[dict],
) -> CoachingEvidenceBundle | None:
    items: list[CoachingEvidenceItem] = []
    role = session.get("role", "Interview")
    summary = session.get("summary") or {}
    average = summary.get("average_score")

    for answer in session.get("answers", []):
        if answer.get("evaluation_status") != "evaluated":
            continue
        evaluation = answer.get("evaluation") or {}
        for strength in (evaluation.get("strengths") or [])[:2]:
            items.append(
                CoachingEvidenceItem(
                    source="interview_session",
                    label="Answer strength",
                    observation=_truncate(strength),
                )
            )
        for gap in (evaluation.get("missing_concepts") or [])[:2]:
            items.append(
                CoachingEvidenceItem(
                    source="interview_session",
                    label="Missing concept",
                    observation=_truncate(gap),
                )
            )

    if resume_analysis:
        analysis = resume_analysis.get("analysis") or {}
        for skill in (analysis.get("skills") or [])[:5]:
            items.append(
                CoachingEvidenceItem(
                    source="resume_analysis",
                    label="Resume skill",
                    observation=_truncate(str(skill)),
                )
            )
        for item in (analysis.get("areas_to_improve") or [])[:3]:
            items.append(
                CoachingEvidenceItem(
                    source="resume_analysis",
                    label="Resume improvement area",
                    observation=_truncate(str(item)),
                )
            )
        for gap in (analysis.get("skill_gaps") or [])[:3]:
            items.append(
                CoachingEvidenceItem(
                    source="resume_analysis",
                    label="Resume skill gap",
                    observation=_truncate(str(gap)),
                )
            )

    from bson import ObjectId

    session_oid = session_id
    for historic in history_sessions[:3]:
        hid = historic.get("_id")
        if isinstance(hid, ObjectId):
            hid = str(hid)
        if str(hid) == str(session_oid):
            continue
        hist_summary = historic.get("summary") or {}
        score = hist_summary.get("average_score")
        if score is not None:
            items.append(
                CoachingEvidenceItem(
                    source="interview_history",
                    label=f"Past interview ({historic.get('role', 'role')})",
                    observation=f"Average score {score}/100",
                )
            )

    if not items:
        return None

    return CoachingEvidenceBundle(
        user_id=user_id,
        session_id=session_id,
        role=role,
        session_average_score=average,
        items=items[:40],
    )
