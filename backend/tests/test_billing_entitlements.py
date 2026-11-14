import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from core.dependencies import get_billing_repository, get_session_repository, get_user_repository
from core.config.settings import settings
from core.security.jwt import create_access_token
from repositories.billing_repository import MeterLimitExceeded
from tests.fake_billing_repository import FakeBillingRepository
from services.entitlement_service import EntitlementError, consume_meter, effective_plan_id
from services.razorpay_billing_service import (
    verify_subscription_signature,
    verify_webhook_signature,
)
from tests.test_auth_routes import InMemorySessionRepository


@pytest.fixture
def billing_client(client: TestClient, sample_user_document: dict):
  billing_repo = FakeBillingRepository()
  user_repo = AsyncMock()
  user_repo.find_by_id = AsyncMock(return_value=sample_user_document)
  from app.main import app

  session_repo = InMemorySessionRepository()
  app.dependency_overrides[get_billing_repository] = lambda: billing_repo
  app.dependency_overrides[get_user_repository] = lambda: user_repo
  app.dependency_overrides[get_session_repository] = lambda: session_repo
  token, _, _ = create_access_token(
    str(sample_user_document["_id"]), sample_user_document["email"]
  )
  headers = {"Authorization": f"Bearer {token}"}
  user_id = str(sample_user_document["_id"])
  yield client, billing_repo, headers, user_id
  app.dependency_overrides.clear()


def test_plan_catalog_public(client: TestClient):
  response = client.get("/api/v1/billing/plans")
  assert response.status_code == 200
  body = response.json()
  assert len(body["plans"]) == 3


@pytest.mark.asyncio
async def test_free_plan_usage_limit():
  repo = FakeBillingRepository()
  user_id = "user-1"
  for _ in range(3):
    await consume_meter(repo, user_id, "resume_analysis", reservation_id=f"r{_}")
  with pytest.raises(EntitlementError):
    await consume_meter(repo, user_id, "resume_analysis", reservation_id="r4")


@pytest.mark.asyncio
async def test_reservation_idempotent():
  repo = FakeBillingRepository()
  user_id = "user-2"
  await consume_meter(repo, user_id, "mock_interview", reservation_id="same-id")
  await consume_meter(repo, user_id, "mock_interview", reservation_id="same-id")
  doc = await repo.get_usage_document(user_id, __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m"))
  assert doc["meters"]["mock_interview"] == 1


def test_invalid_payment_signature():
  assert not verify_subscription_signature("pay_x", "sub_x", "bad-signature")


def test_webhook_signature_roundtrip():
  secret = "whsec_test"
  body = b'{"event":"payment.failed"}'
  sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
  with patch.object(settings, "RAZORPAY_WEBHOOK_SECRET", secret):
    assert verify_webhook_signature(body, sig)
    assert not verify_webhook_signature(body, "wrong")


@pytest.mark.asyncio
async def test_duplicate_webhook_skipped():
  repo = FakeBillingRepository()
  payload = {"event": "subscription.activated"}
  assert await repo.record_webhook_event("evt_1", payload)
  assert not await repo.record_webhook_event("evt_1", payload)


@patch("services.razorpay_billing_service.settings")
def test_dev_checkout_and_verify(mock_settings, billing_client):
  mock_settings.BILLING_DEV_CHECKOUT = True
  mock_settings.razorpay_configured = False
  client, _repo, headers, _ = billing_client
  checkout = client.post(
    "/api/v1/billing/checkout",
    headers=headers,
    json={"plan_id": "pro", "idempotency_key": "idem-12345678"},
  )
  assert checkout.status_code == 200
  sub_id = checkout.json()["razorpay_subscription_id"]
  verify = client.post(
    "/api/v1/billing/verify",
    headers=headers,
    json={
      "razorpay_payment_id": "pay_test",
      "razorpay_subscription_id": sub_id,
      "razorpay_signature": "dev_mode_signature",
    },
  )
  assert verify.status_code == 200
  assert verify.json()["verified"] is True


@pytest.mark.asyncio
async def test_active_pro_plan():
  repo = FakeBillingRepository()
  user_id = "pro-user"
  await repo.upsert_subscription(
    user_id,
    {
      "plan_id": "pro",
      "status": "active",
    },
  )
  assert await effective_plan_id(repo, user_id) == "pro"
