from fastapi import APIRouter, Depends, HTTPException, Request, status

from core.dependencies import get_billing_repository, get_current_user
from models.user_model import UserPublic
from repositories.billing_repository import BillingRepository
from schemas.billing_schema import (
    BillingHistoryItem,
    BillingHistoryResponse,
    BillingOverviewResponse,
    CancelSubscriptionRequest,
    CancelSubscriptionResponse,
    CheckoutRequest,
    CheckoutResponse,
    PlanCatalogResponse,
    PlanCatalogItem,
    SubscriptionSnapshot,
    UsageMeterSnapshot,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
)
from services.entitlement_service import build_usage_snapshot, effective_plan_id
from services.razorpay_billing_service import (
    BillingServiceError,
    cancel_subscription,
    catalog_response,
    create_checkout_subscription,
    process_webhook_event,
    verify_and_activate_payment,
)
from bson import ObjectId

router = APIRouter()


@router.get("/plans", response_model=PlanCatalogResponse)
async def list_plans() -> PlanCatalogResponse:
    data = catalog_response()
    return PlanCatalogResponse(
        currency=data["currency"],
        plans=[PlanCatalogItem.model_validate(item) for item in data["plans"]],
    )


@router.get("/me", response_model=BillingOverviewResponse)
async def billing_overview(
    current_user: UserPublic = Depends(get_current_user),
    billing_repo: BillingRepository = Depends(get_billing_repository),
) -> BillingOverviewResponse:
    plan_id, usage = await build_usage_snapshot(billing_repo, current_user.id)
    sub = await billing_repo.get_subscription_for_user(current_user.id)
    subscription = None
    if sub:
        subscription = SubscriptionSnapshot(
            plan_id=sub.get("plan_id", plan_id),
            status=sub.get("status", "active"),
            current_period_start=sub.get("current_period_start"),
            current_period_end=sub.get("current_period_end"),
            cancel_at_period_end=bool(sub.get("cancel_at_period_end")),
            razorpay_subscription_id=sub.get("razorpay_subscription_id"),
        )
    return BillingOverviewResponse(
        effective_plan_id=plan_id,
        subscription=subscription,
        usage=[UsageMeterSnapshot.model_validate(item) for item in usage],
    )


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(
    payload: CheckoutRequest,
    current_user: UserPublic = Depends(get_current_user),
    billing_repo: BillingRepository = Depends(get_billing_repository),
) -> CheckoutResponse:
    try:
        result = await create_checkout_subscription(
            current_user.id,
            payload.plan_id,
            billing_repo,
            idempotency_key=payload.idempotency_key,
        )
    except BillingServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    return CheckoutResponse(
        key_id=result.get("key_id"),
        razorpay_subscription_id=result["razorpay_subscription_id"],
        plan_id=payload.plan_id,
        dev_mode=bool(result.get("dev_mode")),
    )


@router.post("/verify", response_model=VerifyPaymentResponse)
async def verify_payment(
    payload: VerifyPaymentRequest,
    current_user: UserPublic = Depends(get_current_user),
    billing_repo: BillingRepository = Depends(get_billing_repository),
) -> VerifyPaymentResponse:
    try:
        plan_id = await verify_and_activate_payment(
            current_user.id,
            payload.razorpay_payment_id,
            payload.razorpay_subscription_id,
            payload.razorpay_signature,
            billing_repo,
        )
    except BillingServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    return VerifyPaymentResponse(
        verified=True,
        plan_id=plan_id,
        subscription_status="active",
        message="Subscription activated after server verification.",
    )


@router.post("/cancel", response_model=CancelSubscriptionResponse)
async def cancel(
    payload: CancelSubscriptionRequest,
    current_user: UserPublic = Depends(get_current_user),
    billing_repo: BillingRepository = Depends(get_billing_repository),
) -> CancelSubscriptionResponse:
    try:
        updated = await cancel_subscription(
            current_user.id,
            billing_repo,
            at_period_end=payload.at_period_end,
        )
    except BillingServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    return CancelSubscriptionResponse(
        status=updated.get("status", "cancelled"),
        cancel_at_period_end=bool(updated.get("cancel_at_period_end")),
        current_period_end=updated.get("current_period_end"),
    )


@router.get("/history", response_model=BillingHistoryResponse)
async def billing_history(
    current_user: UserPublic = Depends(get_current_user),
    billing_repo: BillingRepository = Depends(get_billing_repository),
) -> BillingHistoryResponse:
    rows = await billing_repo.list_ledger(current_user.id)
    items = []
    for row in rows:
        items.append(
            BillingHistoryItem(
                id=str(row["_id"]) if isinstance(row.get("_id"), ObjectId) else str(row.get("_id")),
                event_type=row.get("event_type", "event"),
                amount_inr=row.get("amount_inr"),
                status=row.get("status", "unknown"),
                created_at=row["created_at"],
                description=row.get("description", ""),
            )
        )
    return BillingHistoryResponse(items=items)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def razorpay_webhook(
    request: Request,
    billing_repo: BillingRepository = Depends(get_billing_repository),
) -> dict:
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    try:
        processed = await process_webhook_event(raw_body, signature, billing_repo)
    except BillingServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    return {"received": True, "processed": processed}
