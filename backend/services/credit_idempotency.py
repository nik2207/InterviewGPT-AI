from services.entitlement_service import new_reservation_id


def resolve_idempotency_key(header_value: str | None) -> str:
    if header_value and header_value.strip():
        return header_value.strip()
    return new_reservation_id()
