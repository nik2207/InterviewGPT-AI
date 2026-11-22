from datetime import datetime, timedelta, timezone

from core.config.credit_catalog import get_operation_cost, load_credit_catalog
from core.config.plan_catalog import get_plan
from core.config.settings import settings
from repositories.billing_repository import BillingRepository, MeterLimitExceeded
from repositories.credit_repository import CreditRepository, CreditRepositoryError, InsufficientCredits
from services.entitlement_service import (
    EntitlementError,
    active_trial_ends_at,
    consume_meter,
    effective_plan_id,
    resolve_period_key,
    trial_credit_period_key,
)


class CreditServiceError(Exception):
    def __init__(self, message: str, status_code: int = 402) -> None:
        super().__init__(message)
        self.status_code = status_code


async def get_balance_view(
    billing_repo: BillingRepository,
    credit_repo: CreditRepository,
    user_id: str,
) -> dict:
    catalog = load_credit_catalog()
    plan_id = await effective_plan_id(billing_repo, user_id)
    plan = get_plan(plan_id)
    sub = await billing_repo.get_subscription_for_user(user_id)
    trial_end = await active_trial_ends_at(
        billing_repo, user_id, subscription=sub
    )
    period_key = (
        trial_credit_period_key(trial_end)
        if trial_end is not None
        else resolve_period_key(catalog.plan_allowance_meter, sub)
    )
    usage = await billing_repo.get_usage_document(user_id, period_key)
    used = int((usage or {}).get("meters", {}).get(catalog.plan_allowance_meter, 0))
    limit = 10 if trial_end is not None else int(plan.limits.get(catalog.plan_allowance_meter, 0))
    plan_remaining = max(0, limit - used)

    account = await credit_repo.ensure_account(user_id)
    purchased = int(account.get("purchased_balance", 0))
    expiring_soon = 0
    now = datetime.now(timezone.utc)
    for lot in account.get("purchased_lots") or []:
        exp = lot.get("expires_at")
        if isinstance(exp, datetime) and exp <= now + timedelta(days=30):
            expiring_soon += int(lot.get("credits_remaining", 0))

    return {
        "available_total": plan_remaining + purchased,
        "plan_allowance_remaining": plan_remaining,
        "plan_allowance_limit": limit,
        "plan_allowance_used": used,
        "purchased_balance": purchased,
        "purchased_expiring_soon": expiring_soon,
        "period_key": period_key,
    }


async def ensure_ai_operation_allowed(
    billing_repo: BillingRepository,
    credit_repo: CreditRepository,
    user_id: str,
    operation: str,
    *,
    idempotency_key: str,
    try_meter_first: bool = True,
) -> dict:
    existing = await credit_repo.get_transaction_by_idempotency(idempotency_key)
    if existing:
        if existing.get("user_id") != user_id:
            raise CreditServiceError("Invalid idempotency key.", status_code=403)
        if existing.get("status") == "committed":
            return existing
        if existing.get("status") == "refunded":
            raise CreditServiceError("Idempotency key already refunded.", status_code=409)

    op = get_operation_cost(operation)
    sub = await billing_repo.get_subscription_for_user(user_id)
    trial_end = await active_trial_ends_at(
        billing_repo, user_id, subscription=sub
    )

    if try_meter_first and op.meter_fallback and trial_end is None:
        try:
            await consume_meter(
                billing_repo,
                user_id,
                op.meter_fallback,
                reservation_id=f"meter-{idempotency_key}",
            )
            meter_payload = {
                "user_id": user_id,
                "idempotency_key": idempotency_key,
                "operation": operation,
                "amount": 0,
                "source": "plan_allowance",
                "status": "committed",
                "label": op.label,
                "via_meter": op.meter_fallback,
            }
            try:
                return await credit_repo.insert_transaction(meter_payload)
            except CreditRepositoryError as exc:
                if str(exc) == "duplicate_idempotency":
                    existing = await credit_repo.get_transaction_by_idempotency(
                        idempotency_key
                    )
                    if existing:
                        return existing
                raise
        except EntitlementError:
            pass

    cost = op.credit_cost
    plan_id = await effective_plan_id(billing_repo, user_id)
    plan = get_plan(plan_id)
    catalog = load_credit_catalog()
    period_key = (
        trial_credit_period_key(trial_end)
        if trial_end is not None
        else resolve_period_key(catalog.plan_allowance_meter, sub)
    )
    allowance_limit = 10 if trial_end is not None else int(plan.limits.get(catalog.plan_allowance_meter, 0))

    source = "plan_allowance"
    try:
        await billing_repo.increment_meter_by_if_under_limit(
            user_id,
            period_key,
            catalog.plan_allowance_meter,
            cost,
            allowance_limit,
        )
    except MeterLimitExceeded:
        try:
            await credit_repo.debit_purchased(user_id, cost)
            source = "purchased"
        except InsufficientCredits as exc:
            message = (
                "You have used the 10 AI credits included in your 7-day trial. "
                "Upgrade your plan or top up credits to continue."
                if trial_end is not None
                else "Insufficient AI credits. Top up or upgrade your plan."
            )
            raise CreditServiceError(
                message,
                status_code=402,
            ) from exc

    payload = {
        "user_id": user_id,
        "idempotency_key": idempotency_key,
        "operation": operation,
        "amount": cost,
        "source": source,
        "status": "committed",
        "label": op.label,
        "period_key": period_key if source == "plan_allowance" else None,
    }
    try:
        return await credit_repo.insert_transaction(payload)
    except CreditRepositoryError as exc:
        if str(exc) == "duplicate_idempotency":
            existing = await credit_repo.get_transaction_by_idempotency(idempotency_key)
            if existing:
                return existing
        raise
    except Exception:
        if source == "purchased":
            await credit_repo.refund_purchased(user_id, cost)
        else:
            await billing_repo.decrement_meter_by(
                user_id, period_key, catalog.plan_allowance_meter, cost
            )
        raise


async def refund_ai_operation(
    billing_repo: BillingRepository,
    credit_repo: CreditRepository,
    user_id: str,
    *,
    idempotency_key: str,
    refund_idempotency_key: str,
    reason: str = "",
) -> dict:
    existing_refund = await credit_repo.get_transaction_by_idempotency(refund_idempotency_key)
    if existing_refund:
        return existing_refund

    txn = await credit_repo.get_transaction_by_idempotency(idempotency_key)
    if txn is None or txn.get("user_id") != user_id:
        raise CreditServiceError("Charge not found.", status_code=404)
    if txn.get("status") == "refunded":
        return txn

    amount = int(txn.get("amount", 0))
    source = txn.get("source")
    if amount > 0 and source == "purchased":
        await credit_repo.refund_purchased(user_id, amount)
    elif amount > 0 and source == "plan_allowance":
        period_key = txn.get("period_key") or resolve_period_key(
            load_credit_catalog().plan_allowance_meter,
            await billing_repo.get_subscription_for_user(user_id),
        )
        await billing_repo.decrement_meter_by(
            user_id,
            period_key,
            load_credit_catalog().plan_allowance_meter,
            amount,
        )

    updated = await credit_repo.mark_transaction_refunded(
        idempotency_key, refund_idempotency_key
    )
    if updated is None:
        raise CreditServiceError("Unable to refund.", status_code=409)

    await credit_repo.insert_transaction(
        {
            "user_id": user_id,
            "idempotency_key": refund_idempotency_key,
            "operation": txn.get("operation", "refund"),
            "amount": amount,
            "source": "refund",
            "status": "committed",
            "label": f"Refund: {reason or txn.get('label', '')}",
            "refund_of": idempotency_key,
        }
    )
    return updated


async def safe_refund_ai_operation(
    billing_repo: BillingRepository,
    credit_repo: CreditRepository,
    user_id: str,
    *,
    idempotency_key: str,
    reason: str = "",
) -> None:
    try:
        await refund_ai_operation(
            billing_repo,
            credit_repo,
            user_id,
            idempotency_key=idempotency_key,
            refund_idempotency_key=f"refund-{idempotency_key}",
            reason=reason,
        )
    except CreditServiceError:
        return


def verify_order_payment_signature(payment_id: str, order_id: str, signature: str) -> bool:
    if not settings.RAZORPAY_KEY_SECRET.strip():
        return False
    import hashlib
    import hmac

    body = f"{order_id}|{payment_id}".encode()
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.strip().encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature.strip())
