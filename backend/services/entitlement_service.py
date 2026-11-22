from datetime import datetime, timedelta, timezone
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


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


async def active_trial_ends_at(
    billing_repo: BillingRepository,
    user_id: str,
    *,
    subscription: dict | None = None,
) -> datetime | None:
    """Return the active trial expiry, excluding accounts on a paid subscription."""
    if subscription is None:
        subscription = await billing_repo.get_subscription_for_user(user_id)
    if subscription:
        plan_id = subscription.get("plan_id")
        status = subscription.get("status")
        period_end = subscription.get("current_period_end")
        paid_subscription = plan_id in ("pro", "premium") and status in ("active", "cancelled")
        if paid_subscription and (
            status != "cancelled"
            or not isinstance(period_end, datetime)
            or _utc(period_end) >= datetime.now(timezone.utc)
        ):
            return None

    get_user_trial = getattr(billing_repo, "get_user_trial", None)
    user = await get_user_trial(user_id) if get_user_trial else None
    if not user:
        return None
    trial_end = user.get("trial_ends_at")
    if not isinstance(trial_end, datetime):
        created_at = user.get("created_at")
        trial_end = _utc(created_at) + timedelta(days=7) if isinstance(created_at, datetime) else None
    if not isinstance(trial_end, datetime):
        return None
    trial_end = _utc(trial_end)
    return trial_end if trial_end > datetime.now(timezone.utc) else None


def trial_credit_period_key(trial_end: datetime) -> str:
    start = _utc(trial_end) - timedelta(days=7)
    return f"trial-{start.strftime('%Y%m%d')}"


async def effective_plan_id(
    billing_repo: BillingRepository,
    user_id: str,
) -> PlanId:
    sub = await billing_repo.get_subscription_for_user(user_id)
    now = datetime.now(timezone.utc)
    if sub is not None:
        status = sub.get("status", "expired")
        plan_id = sub.get("plan_id", "free")
        if status in ("active", "cancelled") and plan_id in ("free", "pro", "premium"):
            if status != "cancelled":
                return plan_id  # type: ignore[return-value]
            end = sub.get("current_period_end")
            if isinstance(end, datetime) and end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            if not isinstance(end, datetime) or end >= now:
                return plan_id  # type: ignore[return-value]

    trial_end = await active_trial_ends_at(
        billing_repo, user_id, subscription=sub
    )
    if trial_end is not None:
        return "premium"
    return "free"


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
    trial_end = await active_trial_ends_at(
        billing_repo, user_id, subscription=sub
    )
    period_key = (
        trial_credit_period_key(trial_end)
        if meter == "ai_credit" and trial_end is not None
        else resolve_period_key(meter, sub)
    )
    if meter == "ai_credit" and trial_end is not None:
        limit = 10

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
    trial_end = await active_trial_ends_at(
        billing_repo, user_id, subscription=sub
    )

    snapshots = []
    for meter_id, meter_def in catalog.meters.items():
        period_key = (
            trial_credit_period_key(trial_end)
            if meter_id == "ai_credit" and trial_end is not None
            else resolve_period_key(meter_id, sub)
        )
        usage_doc = await billing_repo.get_usage_document(user_id, period_key)
        used = int((usage_doc or {}).get("meters", {}).get(meter_id, 0))
        limit = 10 if meter_id == "ai_credit" and trial_end is not None else int(plan.limits.get(meter_id, 0))
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
