from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SubscriptionStatus = Literal[
    "active",
    "cancelled",
    "expired",
    "past_due",
    "created",
    "halted",
]
PlanId = Literal["free", "pro", "premium"]

BILLING_DISCLAIMER = (
    "Payments are processed by Razorpay. InterviewGPT does not store card numbers. "
    "Access upgrades only after server-side payment verification."
)


class PlanCatalogItem(BaseModel):
    plan_id: PlanId
    display_name: str
    price_inr: int
    limits: dict[str, int]
    features: dict[str, bool]
    tier_rank: int


class PlanCatalogResponse(BaseModel):
    currency: str
    plans: list[PlanCatalogItem]
    disclaimer: str = BILLING_DISCLAIMER


class UsageMeterSnapshot(BaseModel):
    meter: str
    label: str
    used: int
    limit: int
    reset: str


class SubscriptionSnapshot(BaseModel):
    plan_id: PlanId
    status: SubscriptionStatus
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    razorpay_subscription_id: str | None = None


class BillingOverviewResponse(BaseModel):
    effective_plan_id: PlanId
    subscription: SubscriptionSnapshot | None
    usage: list[UsageMeterSnapshot]
    disclaimer: str = BILLING_DISCLAIMER


class CheckoutRequest(BaseModel):
    plan_id: Literal["pro", "premium"]
    idempotency_key: str = Field(..., min_length=8, max_length=64)


class CheckoutResponse(BaseModel):
    key_id: str | None = None
    razorpay_subscription_id: str
    plan_id: PlanId
    dev_mode: bool = False
    disclaimer: str = BILLING_DISCLAIMER


class VerifyPaymentRequest(BaseModel):
    razorpay_payment_id: str = Field(..., min_length=4, max_length=64)
    razorpay_subscription_id: str = Field(..., min_length=4, max_length=64)
    razorpay_signature: str = Field(..., min_length=8, max_length=256)


class VerifyPaymentResponse(BaseModel):
    verified: bool
    plan_id: PlanId
    subscription_status: SubscriptionStatus
    message: str


class CancelSubscriptionRequest(BaseModel):
    at_period_end: bool = True
    reason: str = Field(default="", max_length=500)


class CancelSubscriptionResponse(BaseModel):
    status: SubscriptionStatus
    cancel_at_period_end: bool
    current_period_end: datetime | None = None


class BillingHistoryItem(BaseModel):
    id: str
    event_type: str
    amount_inr: int | None = None
    status: str
    created_at: datetime
    description: str


class BillingHistoryResponse(BaseModel):
    items: list[BillingHistoryItem]
    disclaimer: str = BILLING_DISCLAIMER


class EntitlementErrorResponse(BaseModel):
    code: str
    message: str
    plan_required: PlanId | None = None
    upgrade_path: str = "/pricing"
