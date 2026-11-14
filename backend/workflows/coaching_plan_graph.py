from __future__ import annotations

import logging
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from schemas.coaching_schema import CoachingEvidenceBundle, GeminiCoachingPlanPayload
from services.coaching_gemini_service import (
    CoachingGenerationError,
    generate_coaching_plan,
)

logger = logging.getLogger(__name__)

WorkflowStatus = Literal[
    "insufficient_data",
    "completed",
    "generation_failed",
    "validation_failed",
]


class CoachingGraphState(TypedDict, total=False):
    evidence: CoachingEvidenceBundle | None
    plan: GeminiCoachingPlanPayload | None
    status: WorkflowStatus
    message: str | None


def validate_evidence_node(state: CoachingGraphState) -> CoachingGraphState:
    evidence = state.get("evidence")
    if evidence is None or not evidence.items:
        return {
            "status": "insufficient_data",
            "message": "Not enough saved interview or resume evidence for a coaching plan.",
            "plan": None,
        }
    return {}


def should_generate(state: CoachingGraphState) -> str:
    if state.get("status") == "insufficient_data":
        return "end_insufficient"
    return "generate"


def generate_plan_node(state: CoachingGraphState) -> CoachingGraphState:
    evidence = state.get("evidence")
    if evidence is None:
        return {
            "status": "insufficient_data",
            "message": "Evidence missing.",
            "plan": None,
        }
    try:
        plan = generate_coaching_plan(evidence)
    except CoachingGenerationError as exc:
        return {
            "status": "generation_failed",
            "message": str(exc),
            "plan": None,
        }
    return {"plan": plan, "status": "completed", "message": None}


def validate_plan_node(state: CoachingGraphState) -> CoachingGraphState:
    plan = state.get("plan")
    if state.get("status") != "completed" or plan is None:
        return state
    try:
        GeminiCoachingPlanPayload.model_validate(plan.model_dump())
    except Exception:
        return {
            "status": "validation_failed",
            "message": "Coaching plan failed validation.",
            "plan": None,
        }
    return state


def build_coaching_plan_graph():
    graph = StateGraph(CoachingGraphState)
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


def get_coaching_plan_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_coaching_plan_graph()
    return _compiled_graph


def run_coaching_plan_workflow(
    evidence: CoachingEvidenceBundle | None,
) -> CoachingGraphState:
    graph = get_coaching_plan_graph()
    initial: CoachingGraphState = {"evidence": evidence, "plan": None, "message": None}
    try:
        return graph.invoke(initial)
    except Exception as exc:
        logger.warning("Coaching graph execution failed: %s", type(exc).__name__)
        return {
            "status": "generation_failed",
            "message": "Coaching workflow failed.",
            "plan": None,
            "evidence": evidence,
        }
