from __future__ import annotations

import logging
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from schemas.preparation_plan_schema import (
    GeminiSevenDayPlanPayload,
    PreparationPlanEvidenceBundle,
)
from services.preparation_plan_gemini_service import (
    PreparationPlanGenerationError,
    generate_seven_day_plan,
)

logger = logging.getLogger(__name__)

WorkflowStatus = Literal[
    "insufficient_data",
    "completed",
    "generation_failed",
    "validation_failed",
]


class PreparationPlanGraphState(TypedDict, total=False):
    evidence: PreparationPlanEvidenceBundle | None
    plan: GeminiSevenDayPlanPayload | None
    status: WorkflowStatus
    message: str | None


def validate_evidence_node(state: PreparationPlanGraphState) -> PreparationPlanGraphState:
    evidence = state.get("evidence")
    if evidence is None or not evidence.items:
        return {
            "status": "insufficient_data",
            "message": "Not enough resume, job-match or interview evidence for a 7-day plan.",
            "plan": None,
        }
    return {}


def should_generate(state: PreparationPlanGraphState) -> str:
    if state.get("status") == "insufficient_data":
        return "end_insufficient"
    return "generate"


def generate_plan_node(state: PreparationPlanGraphState) -> PreparationPlanGraphState:
    evidence = state.get("evidence")
    if evidence is None:
        return {
            "status": "insufficient_data",
            "message": "Evidence missing.",
            "plan": None,
        }
    try:
        plan = generate_seven_day_plan(evidence)
    except PreparationPlanGenerationError as exc:
        return {
            "status": "generation_failed",
            "message": str(exc),
            "plan": None,
        }
    return {"plan": plan, "status": "completed", "message": None}


def validate_plan_node(state: PreparationPlanGraphState) -> PreparationPlanGraphState:
    plan = state.get("plan")
    if state.get("status") != "completed" or plan is None:
        return state
    try:
        GeminiSevenDayPlanPayload.model_validate(plan.model_dump())
    except Exception:
        return {
            "status": "validation_failed",
            "message": "Preparation plan failed validation.",
            "plan": None,
        }
    return state


def build_preparation_plan_graph():
    graph = StateGraph(PreparationPlanGraphState)
    graph.add_node("validate_evidence", validate_evidence_node)
    graph.add_node("generate_plan", generate_plan_node)
    graph.add_node("validate_plan", validate_plan_node)

    graph.add_edge(START, "validate_evidence")
    graph.add_conditional_edges(
        "validate_evidence",
        should_generate,
        {
            "end_insufficient": END,
            "generate": "generate_plan",
        },
    )
    graph.add_edge("generate_plan", "validate_plan")
    graph.add_edge("validate_plan", END)
    return graph.compile()


_compiled_graph = None


def get_preparation_plan_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_preparation_plan_graph()
    return _compiled_graph


def run_preparation_plan_workflow(
    evidence: PreparationPlanEvidenceBundle | None,
) -> PreparationPlanGraphState:
    graph = get_preparation_plan_graph()
    initial: PreparationPlanGraphState = {"evidence": evidence, "plan": None, "message": None}
    try:
        return graph.invoke(initial)
    except Exception as exc:
        logger.warning("Preparation plan graph failed: %s", type(exc).__name__)
        return {
            "status": "generation_failed",
            "message": "Preparation workflow failed.",
            "plan": None,
            "evidence": evidence,
        }
