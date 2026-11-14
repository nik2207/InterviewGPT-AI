from datetime import datetime, timezone
from uuid import uuid4

from core.config.plan_catalog import PlanId, get_plan, load_plan_catalog, meter_reset_period
from core.config.settings import settings
from repositories.billing_repository import BillingRepository, MeterLimitExceeded


class EntitlementError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 402,
        code: str = "entitlement_denied",
        plan_required: PlanId | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.plan_required = plan_required


def _monthly_period_key(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y-%m")


def _billing_period_key(subscription: dict | None, now: datetime | None = None) -> str:
    if subscription and subscription.get("current_period_start"):
        start = subscription["current_period_start"]
        if isinstance(start, datetime):
            end = subscription.get("current_period_end")
            end_label = end.strftime("%Y%m%d") if isinstance(end, datetime) else "open"
            return f"cycle-{start.strftime('%Y%m%d')}-{end_label}"
    return _monthly_period_key(now)


def resolve_period_key(
    meter: str,
    subscription: dict | None,
    *,
    now: datetime | None = None,
) -> str:
    reset = meter_reset_period(meter)  # type: ignore[arg-type]
    if reset == "billing_cycle" and subscription:
        return _billing_period_key(subscription, now)
    if reset == "daily":
        now = now or datetime.now(timezone.utc)
        return now.strftime("%Y-%m-%d")
    return _monthly_period_key(now)


async def effective_plan_id(
    billing_repo: BillingRepository,
    user_id: str,
) -> PlanId:
    sub = await billing_repo.get_subscription_for_user(user_id)
    if sub is None:
        return "free"
    status = sub.get("status", "expired")
    plan_id = sub.get("plan_id", "free")
    if status not in ("active", "cancelled"):
        return "free"
    if status == "cancelled":
        end = sub.get("current_period_end")
        now = datetime.now(timezone.utc)
        if isinstance(end, datetime) and end < now:
            return "free"
    if plan_id not in ("free", "pro", "premium"):
        return "free"
    return plan_id  # type: ignore[return-value]


async def require_feature(
    billing_repo: BillingRepository,
    user_id: str,
    feature: str,
    *,
    upgrade_plan: PlanId = "pro",
) -> PlanId:
    plan_id = await effective_plan_id(billing_repo, user_id)
    plan = get_plan(plan_id)
    if not plan.features.get(feature, False):
        raise EntitlementError(
            f"This feature requires the {upgrade_plan.title()} plan.",
            plan_required=upgrade_plan,
        )
    return plan_id


async def consume_meter(
    billing_repo: BillingRepository,
    user_id: str,
    meter: str,
    *,
    reservation_id: str | None = None,
) -> None:
    plan_id = await effective_plan_id(billing_repo, user_id)
    plan = get_plan(plan_id)
    limit = int(plan.limits.get(meter, 0))
    sub = await billing_repo.get_subscription_for_user(user_id)
    period_key = resolve_period_key(meter, sub)

    if reservation_id:
        existing = await billing_repo.get_reservation(reservation_id)
        if existing is not None:
            return

    try:
        await billing_repo.increment_meter_if_under_limit(
            user_id, period_key, meter, limit
        )
    except MeterLimitExceeded as exc:
        suggested: PlanId = "pro" if plan_id == "free" else "premium"
        raise EntitlementError(
            f"Monthly limit reached for {meter.replace('_', ' ')}. Upgrade for more.",
            code="usage_limit_exceeded",
            plan_required=suggested,
        ) from exc

    if reservation_id:
        await billing_repo.reserve_consumption(
            reservation_id,
            {"user_id": user_id, "meter": meter, "period_key": period_key},
        )


async def build_usage_snapshot(
    billing_repo: BillingRepository,
    user_id: str,
) -> tuple[PlanId, list[dict]]:
    catalog = load_plan_catalog()
    plan_id = await effective_plan_id(billing_repo, user_id)
    plan = get_plan(plan_id)
    sub = await billing_repo.get_subscription_for_user(user_id)

    snapshots = []
    for meter_id, meter_def in catalog.meters.items():
        period_key = resolve_period_key(meter_id, sub)
        usage_doc = await billing_repo.get_usage_document(user_id, period_key)
        used = int((usage_doc or {}).get("meters", {}).get(meter_id, 0))
        limit = int(plan.limits.get(meter_id, 0))
        snapshots.append(
            {
                "meter": meter_id,
                "label": meter_def.label,
                "used": used,
                "limit": limit,
                "reset": meter_def.reset,
            }
        )
    return plan_id, snapshots


def new_reservation_id() -> str:
    return uuid4().hex


def redact_coaching_if_needed(evaluation_dict: dict, plan_id: PlanId) -> dict:
    plan = get_plan(plan_id)
    if plan.features.get("detailed_answer_coaching", False):
        return evaluation_dict
    result = dict(evaluation_dict)
    if "improvement_coach" in result:
        result["improvement_coach"] = None
    result["feedback_summary"] = (
        (result.get("feedback_summary") or "")[:600]
        + " Upgrade to Pro for detailed improvement coaching."
    )[:1500]
    return result
