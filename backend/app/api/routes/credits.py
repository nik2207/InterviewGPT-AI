from fastapi import APIRouter, Depends, HTTPException

from core.dependencies import (
    get_billing_repository,
    get_credit_repository,
    get_current_user,
)
from models.user_model import UserPublic
from repositories.billing_repository import BillingRepository
from repositories.credit_repository import CreditRepository
from core.config.credit_catalog import load_credit_catalog
from schemas.credit_schema import (
    ChargeCreditRequest,
    ChargeCreditResponse,
    CreditBalanceResponse,
    CreditCatalogResponse,
    CreditOperationCost,
    CreditTransactionItem,
    CreditTransactionListResponse,
    RefundCreditRequest,
    TopupCheckoutRequest,
    TopupCheckoutResponse,
    TopupVerifyRequest,
)
from services.credit_service import (
    CreditServiceError,
    ensure_ai_operation_allowed,
    get_balance_view,
    refund_ai_operation,
)
from services.credit_topup_service import (
    TopupServiceError,
    start_topup_checkout,
    verify_topup_payment,
)
from repositories.credit_repository import CreditRepository as CreditRepo

router = APIRouter()


@router.get("/catalog", response_model=CreditCatalogResponse)
async def credit_catalog() -> CreditCatalogResponse:
    catalog = load_credit_catalog()
    return CreditCatalogResponse(
        currency=catalog.currency,
        charging_policy=catalog.charging_policy,
        operations=[
            CreditOperationCost(
                operation=op_id,
                label=op.label,
                credit_cost=op.credit_cost,
            )
            for op_id, op in catalog.operations.items()
        ],
        topup_packs=[pack.model_dump() for pack in catalog.topup_packs],
    )


@router.get("/me", response_model=CreditBalanceResponse)
async def credit_balance(
    current_user: UserPublic = Depends(get_current_user),
    billing_repo: BillingRepository = Depends(get_billing_repository),
    credit_repo: CreditRepository = Depends(get_credit_repository),
) -> CreditBalanceResponse:
    data = await get_balance_view(billing_repo, credit_repo, current_user.id)
    return CreditBalanceResponse.model_validate(data)


@router.get("/transactions", response_model=CreditTransactionListResponse)
async def credit_transactions(
    current_user: UserPublic = Depends(get_current_user),
    credit_repo: CreditRepository = Depends(get_credit_repository),
) -> CreditTransactionListResponse:
    rows = await credit_repo.list_transactions(current_user.id)
    items = [
        CreditTransactionItem(
            id=CreditRepo.oid_str(row["_id"]),
            idempotency_key=row["idempotency_key"],
            operation=row.get("operation", ""),
            amount=int(row.get("amount", 0)),
            source=row.get("source", "purchased"),
            status=row.get("status", "committed"),
            created_at=row["created_at"],
            label=row.get("label", ""),
        )
        for row in rows
    ]
    return CreditTransactionListResponse(items=items, total=len(items))


@router.post("/charge", response_model=ChargeCreditResponse)
async def charge_credits(
    payload: ChargeCreditRequest,
    current_user: UserPublic = Depends(get_current_user),
    billing_repo: BillingRepository = Depends(get_billing_repository),
    credit_repo: CreditRepository = Depends(get_credit_repository),
) -> ChargeCreditResponse:
    try:
        txn = await ensure_ai_operation_allowed(
            billing_repo,
            credit_repo,
            current_user.id,
            payload.operation,
            idempotency_key=payload.idempotency_key,
        )
    except CreditServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    return ChargeCreditResponse(
        charged=True,
        amount=int(txn.get("amount", 0)),
        source=txn.get("source", "purchased"),
        idempotency_key=payload.idempotency_key,
        transaction_id=CreditRepo.oid_str(txn["_id"]),
    )


@router.post("/refund", response_model=dict)
async def refund_credits(
    payload: RefundCreditRequest,
    current_user: UserPublic = Depends(get_current_user),
    billing_repo: BillingRepository = Depends(get_billing_repository),
    credit_repo: CreditRepository = Depends(get_credit_repository),
) -> dict:
    try:
        await refund_ai_operation(
            billing_repo,
            credit_repo,
            current_user.id,
            idempotency_key=payload.idempotency_key,
            refund_idempotency_key=payload.refund_idempotency_key,
            reason=payload.reason,
        )
    except CreditServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    return {"refunded": True}


@router.post("/topup/checkout", response_model=TopupCheckoutResponse)
async def topup_checkout(
    payload: TopupCheckoutRequest,
    current_user: UserPublic = Depends(get_current_user),
    credit_repo: CreditRepository = Depends(get_credit_repository),
) -> TopupCheckoutResponse:
    try:
        result = await start_topup_checkout(
            current_user.id,
            payload.pack_id,
            payload.idempotency_key,
            credit_repo,
        )
    except TopupServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    return TopupCheckoutResponse(
        order_id=result["order_id"],
        amount_inr=result["amount_inr"],
        credits=result["credits"],
        key_id=result.get("key_id"),
        dev_mode=bool(result.get("dev_mode")),
    )


@router.post("/topup/verify", response_model=dict)
async def topup_verify(
    payload: TopupVerifyRequest,
    current_user: UserPublic = Depends(get_current_user),
    credit_repo: CreditRepository = Depends(get_credit_repository),
) -> dict:
    try:
        credits = await verify_topup_payment(
            current_user.id,
            payload.pack_id,
            payload.razorpay_payment_id,
            payload.razorpay_order_id,
            payload.razorpay_signature,
            payload.idempotency_key,
            credit_repo,
        )
    except TopupServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    return {"verified": True, "credits_added": credits}
