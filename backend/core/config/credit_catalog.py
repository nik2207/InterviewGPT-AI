import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

_CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "credit_catalog.json"


class CreditOperationDefinition(BaseModel):
    label: str
    credit_cost: int = Field(..., ge=1, le=1000)
    meter_fallback: str | None = None


class CreditTopupPack(BaseModel):
    pack_id: str
    display_name: str
    credits: int = Field(..., ge=1)
    price_inr: int = Field(..., ge=1)
    expiry_days: int | None = None


class CreditCatalog(BaseModel):
    version: int
    currency: str
    charging_policy: str
    plan_allowance_meter: str = "ai_credit"
    operations: dict[str, CreditOperationDefinition]
    topup_packs: list[CreditTopupPack]


@lru_cache
def load_credit_catalog() -> CreditCatalog:
    raw = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    return CreditCatalog.model_validate(raw)


def get_operation_cost(operation: str) -> CreditOperationDefinition:
    catalog = load_credit_catalog()
    op = catalog.operations.get(operation)
    if op is None:
        raise KeyError(f"Unknown credit operation: {operation}")
    return op
