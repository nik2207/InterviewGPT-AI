import logging
from datetime import datetime, timedelta, timezone

import httpx

from core.config.credit_catalog import load_credit_catalog
from core.config.settings import settings
from repositories.credit_repository import CreditRepository
from services.credit_service import CreditServiceError, verify_order_payment_signature

logger = logging.getLogger(__name__)

RAZORPAY_API = "https://api.razorpay.com/v1"


class TopupServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


async def _create_order(amount_paise: int, receipt: str) -> dict:
    if not settings.razorpay_configured:
        raise TopupServiceError("Payments not configured", status_code=503)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{RAZORPAY_API}/orders",
            auth=(settings.RAZORPAY_KEY_ID.strip(), settings.RAZORPAY_KEY_SECRET.strip()),
            json={
                "amount": amount_paise,
                "currency": "INR",
                "receipt": receipt[:40],
                "payment_capture": 1,
            },
        )
    if response.status_code >= 400:
        logger.warning("Razorpay order error: %s", response.text[:200])
        raise TopupServiceError("Unable to create payment order", status_code=502)
    return response.json()


async def start_topup_checkout(
    user_id: str,
    pack_id: str,
    idempotency_key: str,
    credit_repo: CreditRepository,
) -> dict:
    catalog = load_credit_catalog()
    pack = next((p for p in catalog.topup_packs if p.pack_id == pack_id), None)
    if pack is None:
        raise TopupServiceError("Unknown credit pack", status_code=404)

    existing = await credit_repo.get_topup_order(idempotency_key)
    if existing:
        return existing

    if settings.BILLING_DEV_CHECKOUT or not settings.razorpay_configured:
        order_id = f"dev_order_{idempotency_key[:20]}"
        payload = {
            "order_id": order_id,
            "pack_id": pack_id,
            "credits": pack.credits,
            "amount_inr": pack.price_inr,
            "dev_mode": True,
            "user_id": user_id,
        }
        await credit_repo.record_topup_order(idempotency_key, payload)
        return {**payload, "key_id": None}

    order = await _create_order(pack.price_inr * 100, f"cr-{idempotency_key[:16]}")
    order_id = order.get("id")
    if not order_id:
        raise TopupServiceError("Invalid order response", status_code=502)
    payload = {
        "order_id": order_id,
        "pack_id": pack_id,
        "credits": pack.credits,
        "amount_inr": pack.price_inr,
        "dev_mode": False,
        "user_id": user_id,
    }
    await credit_repo.record_topup_order(idempotency_key, payload)
    return {**payload, "key_id": settings.RAZORPAY_KEY_ID.strip()}


async def verify_topup_payment(
    user_id: str,
    pack_id: str,
    payment_id: str,
    order_id: str,
    signature: str,
    idempotency_key: str,
    credit_repo: CreditRepository,
) -> int:
    order = await credit_repo.get_topup_order(idempotency_key)
    if order is None or order.get("user_id") != user_id:
        raise TopupServiceError("Top-up order not found", status_code=404)
    if order.get("pack_id") != pack_id or order.get("order_id") != order_id:
        raise TopupServiceError("Order mismatch", status_code=400)

    catalog = load_credit_catalog()
    pack = next((p for p in catalog.topup_packs if p.pack_id == pack_id), None)
    if pack is None:
        raise TopupServiceError("Unknown pack", status_code=404)

    dev = bool(order.get("dev_mode"))
    if dev and settings.BILLING_DEV_CHECKOUT:
        if signature != "dev_mode_signature":
            raise TopupServiceError("Invalid dev verification", status_code=400)
    elif not verify_order_payment_signature(payment_id, order_id, signature):
        raise TopupServiceError("Payment verification failed", status_code=400)

    existing_credit = await credit_repo.get_transaction_by_idempotency(
        f"topup-{idempotency_key}"
    )
    if existing_credit:
        return int(existing_credit.get("amount", pack.credits))

    expires_at = None
    if pack.expiry_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=pack.expiry_days)

    await credit_repo.credit_purchased(user_id, pack.credits, expires_at=expires_at)
    await credit_repo.insert_transaction(
        {
            "user_id": user_id,
            "idempotency_key": f"topup-{idempotency_key}",
            "operation": "credit_topup",
            "amount": pack.credits,
            "source": "topup",
            "status": "committed",
            "label": pack.display_name,
            "razorpay_payment_id": payment_id,
            "razorpay_order_id": order_id,
        }
    )
    return pack.credits
