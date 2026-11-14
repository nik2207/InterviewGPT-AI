"""Release 4 billing and credits security/regression tests (mocked Razorpay)."""

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from core.config.settings import settings
from core.dependencies import get_billing_repository, get_session_repository, get_user_repository
from core.security.jwt import create_access_token
from services.entitlement_service import effective_plan_id
from services.razorpay_billing_service import BillingServiceError, process_webhook_event
from tests.fake_billing_repository import FakeBillingRepository
from tests.test_auth_routes import InMemorySessionRepository


@pytest.fixture
def commercial_client(client: TestClient, sample_user_document: dict):
    billing_repo = FakeBillingRepository()
    user_repo = AsyncMock()
    user_repo.find_by_id = AsyncMock(return_value=sample_user_document)
    from app.main import app

    session_repo = InMemorySessionRepository()
    app.dependency_overrides[get_billing_repository] = lambda: billing_repo
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo
    token, _, _ = create_access_token(
        str(sample_user_document["_id"]),
        sample_user_document["email"],
    )
    headers = {"Authorization": f"Bearer {token}"}
    user_id = str(sample_user_document["_id"])
    yield client, billing_repo, headers, user_id
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_new_user_defaults_to_free_plan():
    repo = FakeBillingRepository()
    assert await effective_plan_id(repo, "brand-new-user") == "free"


@patch("services.razorpay_billing_service.settings")
def test_checkout_rejects_free_plan(mock_settings, commercial_client):
    mock_settings.BILLING_DEV_CHECKOUT = True
    mock_settings.razorpay_configured = False
    client, _, headers, _ = commercial_client
    response = client.post(
        "/api/v1/billing/checkout",
        headers=headers,
        json={"plan_id": "free", "idempotency_key": "free-plan-12345678"},
    )
    assert response.status_code == 422


@patch("services.razorpay_billing_service.settings")
def test_verify_rejects_wrong_subscription(mock_settings, commercial_client):
    mock_settings.BILLING_DEV_CHECKOUT = True
    mock_settings.razorpay_configured = False
    client, _billing, headers, _user_id = commercial_client
    checkout = client.post(
        "/api/v1/billing/checkout",
        headers=headers,
        json={"plan_id": "pro", "idempotency_key": "wrong-sub-12345678"},
    )
    assert checkout.status_code == 200
    real_sub = checkout.json()["razorpay_subscription_id"]
    response = client.post(
        "/api/v1/billing/verify",
        headers=headers,
        json={
            "razorpay_payment_id": "pay_x",
            "razorpay_subscription_id": f"{real_sub}_tampered",
            "razorpay_signature": "dev_mode_signature",
        },
    )
    assert response.status_code == 403


@patch("services.razorpay_billing_service.settings")
def test_dev_verify_rejects_bad_signature(mock_settings, commercial_client):
    mock_settings.BILLING_DEV_CHECKOUT = True
    mock_settings.razorpay_configured = False
    client, _billing, headers, _user_id = commercial_client
    checkout = client.post(
        "/api/v1/billing/checkout",
        headers=headers,
        json={"plan_id": "pro", "idempotency_key": "sig-test-12345678"},
    )
    sub_id = checkout.json()["razorpay_subscription_id"]
    response = client.post(
        "/api/v1/billing/verify",
        headers=headers,
        json={
            "razorpay_payment_id": "pay_x",
            "razorpay_subscription_id": sub_id,
            "razorpay_signature": "not_dev_mode_signature",
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_signature():
    repo = FakeBillingRepository()
    with pytest.raises(BillingServiceError) as exc:
        await process_webhook_event(b"{}", "bad-sig", repo)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_webhook_payment_failed_marks_past_due():
    repo = FakeBillingRepository()
    user_id = "pay-fail-user"
    await repo.upsert_subscription(
        user_id,
        {"plan_id": "pro", "status": "active", "razorpay_subscription_id": "sub_pf"},
    )
    body_dict = {
        "event": "payment.failed",
        "id": "evt_payment_failed_1",
        "payload": {
            "subscription": {
                "entity": {
                    "id": "sub_pf",
                    "notes": {"user_id": user_id, "plan_id": "pro"},
                }
            }
        },
    }
    body = json.dumps(body_dict).encode()
    secret = "whsec_release4_test"
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    with patch.object(settings, "RAZORPAY_WEBHOOK_SECRET", secret):
        processed = await process_webhook_event(body, sig, repo)
    assert processed is True
    sub = await repo.get_subscription_for_user(user_id)
    assert sub["status"] == "past_due"


@pytest.mark.asyncio
async def test_webhook_duplicate_idempotent():
    repo = FakeBillingRepository()
    user_id = "dup-webhook"
    body_dict = {
        "event": "subscription.activated",
        "id": "evt_dup_1",
        "payload": {
            "subscription": {
                "entity": {
                    "id": "sub_dup",
                    "notes": {"user_id": user_id, "plan_id": "pro"},
                    "payment_id": "pay_1",
                }
            }
        },
    }
    body = json.dumps(body_dict).encode()
    secret = "whsec_dup"
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    with patch.object(settings, "RAZORPAY_WEBHOOK_SECRET", secret):
        first = await process_webhook_event(body, sig, repo)
        second = await process_webhook_event(body, sig, repo)
    assert first is True
    assert second is False


@patch("services.razorpay_billing_service.settings")
def test_full_dev_subscribe_cancel_flow(mock_settings, commercial_client):
    """Register → checkout → verify → billing/me → cancel (dev mode only)."""
    mock_settings.BILLING_DEV_CHECKOUT = True
    mock_settings.razorpay_configured = False
    client, billing, headers, user_id = commercial_client

    overview = client.get("/api/v1/billing/me", headers=headers)
    assert overview.status_code == 200
    assert overview.json()["effective_plan_id"] == "free"

    checkout = client.post(
        "/api/v1/billing/checkout",
        headers=headers,
        json={"plan_id": "pro", "idempotency_key": "flow-key-12345678"},
    )
    assert checkout.status_code == 200
    sub_id = checkout.json()["razorpay_subscription_id"]

    verify = client.post(
        "/api/v1/billing/verify",
        headers=headers,
        json={
            "razorpay_payment_id": "pay_flow",
            "razorpay_subscription_id": sub_id,
            "razorpay_signature": "dev_mode_signature",
        },
    )
    assert verify.status_code == 200
    assert verify.json()["plan_id"] == "pro"

    overview2 = client.get("/api/v1/billing/me", headers=headers)
    assert overview2.json()["effective_plan_id"] == "pro"

    cancel = client.post(
        "/api/v1/billing/cancel",
        headers=headers,
        json={"at_period_end": False},
    )
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"


def test_webhook_endpoint_rejects_bad_signature(client: TestClient):
    response = client.post(
        "/api/v1/billing/webhook",
        content=b'{"event":"test"}',
        headers={"X-Razorpay-Signature": "invalid"},
    )
    assert response.status_code == 400
