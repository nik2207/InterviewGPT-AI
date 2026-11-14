import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

PlanId = Literal["free", "pro", "premium"]
MeterId = Literal[
    "resume_analysis",
    "mock_interview",
    "job_match",
    "preparation_plan",
    "career_readiness",
    "voice_interview",
    "ai_credit",
    "premium_report_pdf",
]
ResetPeriod = Literal["monthly", "billing_cycle", "daily"]
FeatureId = Literal[
    "job_matching",
    "detailed_answer_coaching",
    "preparation_plans",
    "career_readiness",
    "voice_interview",
    "premium_analytics",
    "basic_interview_history",
]

_CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "plan_catalog.json"


class MeterDefinition(BaseModel):
    label: str
    reset: ResetPeriod


class PlanDefinition(BaseModel):
    display_name: str
    tier_rank: int
    price_inr: int
    razorpay_plan_id_setting: str | None = None
    limits: dict[str, int]
    features: dict[str, bool]


class PlanCatalog(BaseModel):
    version: int
    currency: str
    meters: dict[str, MeterDefinition]
    plans: dict[str, PlanDefinition]


@lru_cache
def load_plan_catalog() -> PlanCatalog:
    raw = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    return PlanCatalog.model_validate(raw)


def get_plan(plan_id: PlanId) -> PlanDefinition:
    catalog = load_plan_catalog()
    plan = catalog.plans.get(plan_id)
    if plan is None:
        raise KeyError(f"Unknown plan: {plan_id}")
    return plan


def meter_reset_period(meter: MeterId) -> ResetPeriod:
    catalog = load_plan_catalog()
    return catalog.meters[meter].reset
