from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CreditTransactionStatus = Literal["committed", "refunded"]
CreditSource = Literal["plan_allowance", "purchased", "topup", "refund"]


class CreditOperationCost(BaseModel):
    operation: str
    label: str
    credit_cost: int


class CreditCatalogResponse(BaseModel):
    currency: str
    charging_policy: str
    operations: list[CreditOperationCost]
    topup_packs: list[dict]


class CreditBalanceResponse(BaseModel):
    available_total: int
    plan_allowance_remaining: int
    plan_allowance_limit: int
    plan_allowance_used: int
    purchased_balance: int
    purchased_expiring_soon: int
    period_key: str
    disclaimer: str = (
        "Balances are computed on the server. Purchased credits and plan allowances are separate pools."
    )


class CreditTransactionItem(BaseModel):
    id: str
    idempotency_key: str
    operation: str
    amount: int
    source: CreditSource
    status: CreditTransactionStatus
    created_at: datetime
    label: str = ""


class CreditTransactionListResponse(BaseModel):
    items: list[CreditTransactionItem]
    total: int


class ChargeCreditRequest(BaseModel):
    operation: str = Field(..., min_length=2, max_length=64)
    idempotency_key: str = Field(..., min_length=8, max_length=64)


class ChargeCreditResponse(BaseModel):
    charged: bool
    amount: int
    source: CreditSource
    idempotency_key: str
    transaction_id: str


class RefundCreditRequest(BaseModel):
    idempotency_key: str = Field(..., min_length=8, max_length=64)
    refund_idempotency_key: str = Field(..., min_length=8, max_length=64)
    reason: str = Field(default="", max_length=300)


class TopupCheckoutRequest(BaseModel):
    pack_id: str = Field(..., min_length=3, max_length=40)
    idempotency_key: str = Field(..., min_length=8, max_length=64)


class TopupCheckoutResponse(BaseModel):
    order_id: str
    amount_inr: int
    credits: int
    key_id: str | None = None
    dev_mode: bool = False


class TopupVerifyRequest(BaseModel):
    razorpay_payment_id: str = Field(..., min_length=4, max_length=64)
    razorpay_order_id: str = Field(..., min_length=4, max_length=64)
    razorpay_signature: str = Field(..., min_length=8, max_length=256)
    pack_id: str = Field(..., min_length=3, max_length=40)
    idempotency_key: str = Field(..., min_length=8, max_length=64)
