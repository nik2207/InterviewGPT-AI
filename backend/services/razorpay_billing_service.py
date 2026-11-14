import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from core.config.plan_catalog import PlanId, get_plan, load_plan_catalog
from core.config.settings import settings
from repositories.billing_repository import BillingRepository

logger = logging.getLogger(__name__)

RAZORPAY_API = "https://api.razorpay.com/v1"


class BillingServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _resolve_razorpay_plan_id(plan_id: PlanId) -> str:
    plan = get_plan(plan_id)
    setting_name = plan.razorpay_plan_id_setting
    if not setting_name:
        raise BillingServiceError("Plan is not billable.", status_code=400)
    value = getattr(settings, setting_name, "") or ""
    if not value.strip():
        raise BillingServiceError(
            f"Razorpay plan id not configured ({setting_name}).",
            status_code=503,
        )
    return value.strip()


async def _razorpay_request(method: str, path: str, payload: dict | None = None) -> dict:
    if not settings.razorpay_configured:
        raise BillingServiceError("Razorpay is not configured.", status_code=503)
    auth = (settings.RAZORPAY_KEY_ID.strip(), settings.RAZORPAY_KEY_SECRET.strip())
    url = f"{RAZORPAY_API}{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(method, url, auth=auth, json=payload)
    if response.status_code >= 400:
        logger.warning("Razorpay API error %s: %s", response.status_code, response.text[:300])
        raise BillingServiceError("Payment provider request failed.", status_code=502)
    if not response.text.strip():
        return {}
    return response.json()


def verify_subscription_signature(
    payment_id: str,
    subscription_id: str,
    signature: str,
) -> bool:
    if not settings.RAZORPAY_KEY_SECRET.strip():
        return False
    body = f"{payment_id}|{subscription_id}".encode()
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.strip().encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature.strip())


def verify_webhook_signature(raw_body: bytes, signature: str | None) -> bool:
    secret = settings.RAZORPAY_WEBHOOK_SECRET.strip()
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip())


async def create_checkout_subscription(
    user_id: str,
    plan_id: PlanId,
    billing_repo: BillingRepository,
    *,
    idempotency_key: str,
) -> dict:
    if plan_id not in ("pro", "premium"):
        raise BillingServiceError("Invalid paid plan.", status_code=400)

    existing = await billing_repo.get_reservation(f"checkout-{idempotency_key}")
    if existing and existing.get("razorpay_subscription_id"):
        return existing

    if settings.BILLING_DEV_CHECKOUT or not settings.razorpay_configured:
        sub_id = f"dev_sub_{idempotency_key[:24]}"
        await billing_repo.reserve_consumption(
            f"checkout-{idempotency_key}",
            {
                "user_id": user_id,
                "plan_id": plan_id,
                "razorpay_subscription_id": sub_id,
                "dev_mode": True,
            },
        )
        await billing_repo.upsert_subscription(
            user_id,
            {
                "plan_id": plan_id,
                "status": "created",
                "razorpay_subscription_id": sub_id,
                "cancel_at_period_end": False,
            },
        )
        return {
            "razorpay_subscription_id": sub_id,
            "key_id": None,
            "dev_mode": True,
        }

    razorpay_plan = _resolve_razorpay_plan_id(plan_id)
    payload = {
        "plan_id": razorpay_plan,
        "total_count": 12,
        "customer_notify": 1,
        "notes": {"user_id": user_id, "plan_id": plan_id, "idempotency_key": idempotency_key},
    }
    data = await _razorpay_request("POST", "/subscriptions", payload)
    sub_id = data.get("id")
    if not sub_id:
        raise BillingServiceError("Invalid subscription response.", status_code=502)

    await billing_repo.reserve_consumption(
        f"checkout-{idempotency_key}",
        {
            "user_id": user_id,
            "plan_id": plan_id,
            "razorpay_subscription_id": sub_id,
            "dev_mode": False,
        },
    )
    await billing_repo.upsert_subscription(
        user_id,
        {
            "plan_id": plan_id,
            "status": "created",
            "razorpay_subscription_id": sub_id,
            "cancel_at_period_end": False,
        },
    )
    return {
        "razorpay_subscription_id": sub_id,
        "key_id": settings.RAZORPAY_KEY_ID.strip(),
        "dev_mode": False,
    }


async def activate_subscription_after_verify(
    user_id: str,
    plan_id: PlanId,
    razorpay_subscription_id: str,
    razorpay_payment_id: str,
    billing_repo: BillingRepository,
) -> dict:
    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=30)
    updated = await billing_repo.upsert_subscription(
        user_id,
        {
            "plan_id": plan_id,
            "status": "active",
            "razorpay_subscription_id": razorpay_subscription_id,
            "last_payment_id": razorpay_payment_id,
            "current_period_start": now,
            "current_period_end": period_end,
            "cancel_at_period_end": False,
        },
    )
    await billing_repo.append_ledger_entry(
        user_id,
        {
            "event_type": "payment_captured",
            "status": "success",
            "amount_inr": get_plan(plan_id).price_inr,
            "description": f"{get_plan(plan_id).display_name} subscription activated",
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_subscription_id": razorpay_subscription_id,
        },
    )
    return updated


async def verify_and_activate_payment(
    user_id: str,
    payment_id: str,
    subscription_id: str,
    signature: str,
    billing_repo: BillingRepository,
) -> PlanId:
    sub_doc = await billing_repo.get_subscription_for_user(user_id)
    if sub_doc is None or sub_doc.get("razorpay_subscription_id") != subscription_id:
        raise BillingServiceError("Subscription does not match user.", status_code=403)

    plan_id: PlanId = sub_doc.get("plan_id", "pro")  # type: ignore[assignment]
    dev_mode = subscription_id.startswith("dev_sub_")

    if dev_mode and settings.BILLING_DEV_CHECKOUT:
        if signature != "dev_mode_signature":
            raise BillingServiceError("Invalid dev verification.", status_code=400)
    elif not verify_subscription_signature(payment_id, subscription_id, signature):
        raise BillingServiceError("Payment signature verification failed.", status_code=400)

    await activate_subscription_after_verify(
        user_id,
        plan_id,
        subscription_id,
        payment_id,
        billing_repo,
    )
    return plan_id


async def cancel_subscription(
    user_id: str,
    billing_repo: BillingRepository,
    *,
    at_period_end: bool,
) -> dict:
    sub = await billing_repo.get_subscription_for_user(user_id)
    if sub is None or sub.get("status") not in ("active", "created", "past_due"):
        raise BillingServiceError("No active subscription to cancel.", status_code=404)

    razorpay_id = sub.get("razorpay_subscription_id")
    if (
        razorpay_id
        and not str(razorpay_id).startswith("dev_sub_")
        and settings.razorpay_configured
        and not at_period_end
    ):
        await _razorpay_request(
            "POST",
            f"/subscriptions/{razorpay_id}/cancel",
            {"cancel_at_cycle_end": 0},
        )
        status = "cancelled"
    elif at_period_end:
        status = sub.get("status", "active")
    else:
        status = "cancelled"

    fields = {
        "cancel_at_period_end": at_period_end,
        "status": status if not at_period_end else sub.get("status", "active"),
        "cancelled_at": datetime.now(timezone.utc) if not at_period_end else sub.get("cancelled_at"),
    }
    if not at_period_end:
        fields["status"] = "cancelled"
        fields["current_period_end"] = datetime.now(timezone.utc)

    updated = await billing_repo.upsert_subscription(user_id, fields)
    await billing_repo.append_ledger_entry(
        user_id,
        {
            "event_type": "subscription_cancelled",
            "status": "success",
            "description": "Subscription cancelled"
            + (" at period end" if at_period_end else " immediately"),
        },
    )
    return updated


async def process_webhook_event(
    raw_body: bytes,
    signature: str | None,
    billing_repo: BillingRepository,
) -> bool:
    if not verify_webhook_signature(raw_body, signature):
        raise BillingServiceError("Invalid webhook signature.", status_code=400)

    payload = json.loads(raw_body.decode("utf-8"))
    event_id = payload.get("event") or payload.get("id") or hashlib.sha256(raw_body).hexdigest()
    if not await billing_repo.record_webhook_event(str(event_id), payload):
        return False

    event_type = payload.get("event", "")
    entity = (payload.get("payload") or {}).get("subscription", {}).get("entity") or {}
    notes = entity.get("notes") or {}
    user_id = notes.get("user_id")
    plan_id = notes.get("plan_id", "pro")
    razorpay_sub_id = entity.get("id")

    if event_type == "subscription.activated" and user_id and razorpay_sub_id:
        await activate_subscription_after_verify(
            user_id,
            plan_id,  # type: ignore[arg-type]
            razorpay_sub_id,
            entity.get("payment_id") or "webhook",
            billing_repo,
        )
    elif event_type in ("subscription.cancelled", "subscription.completed"):
        if user_id:
            await billing_repo.upsert_subscription(
                user_id,
                {
                    "status": "cancelled" if event_type == "subscription.cancelled" else "expired",
                    "current_period_end": datetime.now(timezone.utc),
                },
            )
    elif event_type in ("subscription.halted", "payment.failed"):
        if user_id:
            await billing_repo.upsert_subscription(
                user_id,
                {"status": "past_due"},
            )
            await billing_repo.append_ledger_entry(
                user_id,
                {
                    "event_type": event_type,
                    "status": "failed",
                    "description": "Renewal payment failed",
                },
            )

    contained = payload.get("payload") or {}
    payment_entity = (contained.get("payment") or {}).get("entity") or {}
    if payment_entity.get("id") and user_id:
        await billing_repo.append_ledger_entry(
            user_id,
            {
                "event_type": event_type or "payment_event",
                "status": payment_entity.get("status", "unknown"),
                "amount_inr": int((payment_entity.get("amount") or 0) // 100),
                "description": f"Razorpay {event_type}",
                "razorpay_payment_id": payment_entity.get("id"),
            },
        )
    return True


def catalog_response() -> dict:
    catalog = load_plan_catalog()
    plans = []
    for plan_id, plan in catalog.plans.items():
        plans.append(
            {
                "plan_id": plan_id,
                "display_name": plan.display_name,
                "price_inr": plan.price_inr,
                "limits": plan.limits,
                "features": plan.features,
                "tier_rank": plan.tier_rank,
            }
        )
    plans.sort(key=lambda item: item["tier_rank"])
    return {"currency": catalog.currency, "plans": plans}
