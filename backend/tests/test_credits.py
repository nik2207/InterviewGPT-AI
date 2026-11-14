import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from core.dependencies import (
    get_billing_repository,
    get_credit_repository,
    get_session_repository,
    get_user_repository,
)
from core.security.jwt import create_access_token
from services.credit_service import (
    CreditServiceError,
    ensure_ai_operation_allowed,
    get_balance_view,
    refund_ai_operation,
)
from tests.fake_billing_repository import FakeBillingRepository
from tests.fake_credit_repository import FakeCreditRepository
from tests.test_auth_routes import InMemorySessionRepository


def _exhaust_meter_allowances(billing: FakeBillingRepository, user_id: str) -> None:
    from services.entitlement_service import resolve_period_key

    period = resolve_period_key("ai_credit", None)
    billing.usage[(user_id, period)] = {
        "meters": {"resume_analysis": 3, "ai_credit": 10},
    }


@pytest.fixture(autouse=True)
def enable_credit_dev_checkout(monkeypatch):
    from core.config.settings import settings

    monkeypatch.setattr(settings, "BILLING_DEV_CHECKOUT", True)


@pytest.fixture
def credits_client(client: TestClient, sample_user_document: dict):
    billing_repo = FakeBillingRepository()
    credit_repo = FakeCreditRepository()
    user_repo = AsyncMock()
    user_repo.find_by_id = AsyncMock(return_value=sample_user_document)
    from app.main import app

    session_repo = InMemorySessionRepository()
    app.dependency_overrides[get_billing_repository] = lambda: billing_repo
    app.dependency_overrides[get_credit_repository] = lambda: credit_repo
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo
    token, _, _ = create_access_token(
        str(sample_user_document["_id"]), sample_user_document["email"]
    )
    headers = {"Authorization": f"Bearer {token}"}
    user_id = str(sample_user_document["_id"])
    yield client, billing_repo, credit_repo, headers, user_id
    app.dependency_overrides.clear()


def test_credit_catalog_public(client: TestClient):
    response = client.get("/api/v1/credits/catalog")
    assert response.status_code == 200
    body = response.json()
    assert body["currency"] == "INR"
    assert any(op["operation"] == "resume_analysis" for op in body["operations"])


def test_credit_balance_requires_auth(client: TestClient):
    assert client.get("/api/v1/credits/me").status_code == 401


def test_topup_dev_verify(credits_client):
    client, _billing, _credit, headers, _user_id = credits_client
    key = "topup-key-12345678"
    checkout = client.post(
        "/api/v1/credits/topup/checkout",
        json={"pack_id": "pack_50", "idempotency_key": key},
        headers=headers,
    )
    assert checkout.status_code == 200
    body = checkout.json()
    assert body["dev_mode"] is True
    verify = client.post(
        "/api/v1/credits/topup/verify",
        json={
            "pack_id": "pack_50",
            "razorpay_payment_id": "pay_dev",
            "razorpay_order_id": body["order_id"],
            "razorpay_signature": "dev_mode_signature",
            "idempotency_key": key,
        },
        headers=headers,
    )
    assert verify.status_code == 200
    assert verify.json()["credits_added"] == 50
    retry = client.post(
        "/api/v1/credits/topup/verify",
        json={
            "pack_id": "pack_50",
            "razorpay_payment_id": "pay_dev",
            "razorpay_order_id": body["order_id"],
            "razorpay_signature": "dev_mode_signature",
            "idempotency_key": key,
        },
        headers=headers,
    )
    assert retry.status_code == 200
    assert retry.json()["credits_added"] == 50
    balance = client.get("/api/v1/credits/me", headers=headers)
    assert balance.status_code == 200
    assert balance.json()["purchased_balance"] == 50


def test_charge_idempotent_via_api(credits_client):
    client, billing, credit_repo, headers, user_id = credits_client
    _exhaust_meter_allowances(billing, user_id)
    credit_repo.add_purchased_balance(user_id, 20)
    payload = {
        "operation": "resume_analysis",
        "idempotency_key": "api-charge-12345678",
    }
    first = client.post("/api/v1/credits/charge", json=payload, headers=headers)
    second = client.post("/api/v1/credits/charge", json=payload, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["transaction_id"] == second.json()["transaction_id"]
    balance = client.get("/api/v1/credits/me", headers=headers)
    assert balance.json()["purchased_balance"] == 17


@pytest.mark.asyncio
async def test_idempotent_charge():
    billing = FakeBillingRepository()
    credit = FakeCreditRepository()
    user_id = "user-a"
    _exhaust_meter_allowances(billing, user_id)
    credit.add_purchased_balance(user_id, 20)
    key = "charge-key-12345678"
    first = await ensure_ai_operation_allowed(
        billing, credit, user_id, "resume_analysis", idempotency_key=key
    )
    second = await ensure_ai_operation_allowed(
        billing, credit, user_id, "resume_analysis", idempotency_key=key
    )
    assert first["idempotency_key"] == second["idempotency_key"]
    balance = await get_balance_view(billing, credit, user_id)
    assert balance["purchased_balance"] == 17


@pytest.mark.asyncio
async def test_insufficient_balance():
    billing = FakeBillingRepository()
    credit = FakeCreditRepository()
    user_id = "user-b"
    _exhaust_meter_allowances(billing, user_id)
    with pytest.raises(CreditServiceError) as exc:
        await ensure_ai_operation_allowed(
            billing,
            credit,
            user_id,
            "voice_interview_session",
            idempotency_key="voice-12345678",
        )
    assert exc.value.status_code == 402


@pytest.mark.asyncio
async def test_refund_restores_purchased():
    billing = FakeBillingRepository()
    credit = FakeCreditRepository()
    user_id = "user-c"
    credit.add_purchased_balance(user_id, 30)
    key = "op-key-123456789"
    await ensure_ai_operation_allowed(
        billing, credit, user_id, "job_match", idempotency_key=key
    )
    await refund_ai_operation(
        billing,
        credit,
        user_id,
        idempotency_key=key,
        refund_idempotency_key=f"refund-{key}",
    )
    balance = await get_balance_view(billing, credit, user_id)
    assert balance["purchased_balance"] == 30


@pytest.mark.asyncio
async def test_concurrent_debit_does_not_overspend():
    billing = FakeBillingRepository()
    credit = FakeCreditRepository()
    user_id = "user-d"
    _exhaust_meter_allowances(billing, user_id)
    credit.add_purchased_balance(user_id, 10)

    async def attempt(i: int):
        try:
            await ensure_ai_operation_allowed(
                billing,
                credit,
                user_id,
                "resume_analysis",
                idempotency_key=f"concurrent-{i:02d}-123456",
            )
            return True
        except CreditServiceError:
            return False

    results = await asyncio.gather(*(attempt(i) for i in range(5)))
    success = sum(1 for r in results if r)
    assert success == 3
    balance = await get_balance_view(billing, credit, user_id)
    assert balance["purchased_balance"] == 1


def test_refund_without_prior_charge_returns_404(credits_client):
    client, _b, _c, headers, _ = credits_client
    response = client.post(
        "/api/v1/credits/refund",
        headers=headers,
        json={
            "idempotency_key": "never-charged-key-12345",
            "refund_idempotency_key": "refund-never-12345678",
        },
    )
    assert response.status_code == 404


def test_topup_verify_order_mismatch(credits_client):
    client, _b, _c, headers, _ = credits_client
    key = "mismatch-key-12345678"
    checkout = client.post(
        "/api/v1/credits/topup/checkout",
        json={"pack_id": "pack_50", "idempotency_key": key},
        headers=headers,
    )
    order_id = checkout.json()["order_id"]
    response = client.post(
        "/api/v1/credits/topup/verify",
        json={
            "pack_id": "pack_50",
            "razorpay_payment_id": "pay_dev",
            "razorpay_order_id": f"{order_id}-wrong",
            "razorpay_signature": "dev_mode_signature",
            "idempotency_key": key,
        },
        headers=headers,
    )
    assert response.status_code == 400
