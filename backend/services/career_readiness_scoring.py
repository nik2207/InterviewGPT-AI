from schemas.career_readiness_schema import (
    READINESS_SCORING_RULES,
    ComponentScoreSection,
    OverallReadinessIndicator,
)

COMPONENT_WEIGHTS: dict[str, float] = {
    "alignment": 0.25,
    "technical": 0.20,
    "relevance": 0.15,
    "completeness": 0.15,
    "structure": 0.10,
    "interview_performance": 0.10,
    "preparation": 0.05,
}


def dimension_to_percent(values: list[int]) -> float | None:
    if not values:
        return None
    avg = sum(values) / len(values)
    return round((avg / 5.0) * 100.0, 1)


def collect_dimension_scores(sessions: list[dict]) -> dict[str, list[int]]:
    buckets: dict[str, list[int]] = {
        "technical_correctness": [],
        "relevance": [],
        "completeness": [],
        "answer_structure": [],
    }
    for session in sessions:
        for answer in session.get("answers", []):
            if answer.get("evaluation_status") != "evaluated":
                continue
            evaluation = answer.get("evaluation") or {}
            dims = evaluation.get("dimension_scores") or {}
            for key in buckets:
                value = dims.get(key)
                if isinstance(value, (int, float)) and 1 <= value <= 5:
                    buckets[key].append(int(value))
    return buckets


def collect_session_scores(sessions: list[dict]) -> list[float]:
    scores: list[float] = []
    for session in sessions:
        summary = session.get("summary") or {}
        avg = summary.get("average_score")
        if avg is not None:
            scores.append(float(avg))
    return scores


def compute_overall_readiness(
    *,
    alignment: float | None,
    technical: float | None,
    relevance: float | None,
    completeness: float | None,
    structure: float | None,
    interview_performance: float | None,
    preparation: float | None,
) -> OverallReadinessIndicator:
    has_interview_dims = any(
        v is not None for v in (technical, relevance, completeness, structure, interview_performance)
    )
    if not has_interview_dims:
        return OverallReadinessIndicator(
            score=None,
            status="insufficient_data",
            message="Not enough practice data — complete mock interviews with evaluated answers.",
        )

    components = {
        "alignment": alignment,
        "technical": technical,
        "relevance": relevance,
        "completeness": completeness,
        "structure": structure,
        "interview_performance": interview_performance,
        "preparation": preparation,
    }

    weight_sum = 0.0
    weighted = 0.0
    for key, weight in COMPONENT_WEIGHTS.items():
        value = components.get(key)
        if value is not None:
            weight_sum += weight
            weighted += value * weight

    if weight_sum == 0:
        return OverallReadinessIndicator(
            score=None,
            status="insufficient_data",
            message="Not enough practice data.",
        )

    score = round(weighted / weight_sum, 1)
    return OverallReadinessIndicator(
        score=score,
        status="available",
        message=f"Based on {int(weight_sum * 100)}% of defined weight from available data sources.",
    )


def make_component(
    score: float | None,
    *,
    detail: str,
    sample_size: int = 0,
) -> ComponentScoreSection:
    if score is None:
        return ComponentScoreSection(
            score=None,
            status="insufficient_data",
            detail=detail or "Not enough practice data.",
            sample_size=sample_size,
        )
    return ComponentScoreSection(
        score=score,
        status="available",
        detail=detail,
        sample_size=sample_size,
    )


def get_scoring_rules() -> str:
    return READINESS_SCORING_RULES
