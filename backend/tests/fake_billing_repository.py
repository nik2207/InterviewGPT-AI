from repositories.billing_repository import BillingRepository, MeterLimitExceeded


class FakeBillingRepository(BillingRepository):
    """In-memory billing repo for API tests (no Mongo)."""

    def __init__(self) -> None:
        self.subscriptions: dict[str, dict] = {}
        self.usage: dict[tuple[str, str], dict] = {}
        self.webhooks: set[str] = set()
        self.ledger: list[dict] = []
        self.reservations: dict[str, dict] = {}
        self._indexes_ensured = True

    async def ensure_indexes(self) -> None:
        return None

    async def get_subscription_for_user(self, user_id: str):
        return self.subscriptions.get(user_id)

    async def get_subscription_by_razorpay_id(self, razorpay_subscription_id: str):
        for sub in self.subscriptions.values():
            if sub.get("razorpay_subscription_id") == razorpay_subscription_id:
                return sub
        return None

    async def upsert_subscription(self, user_id: str, fields: dict):
        doc = {**self.subscriptions.get(user_id, {}), **fields, "user_id": user_id}
        self.subscriptions[user_id] = doc
        return doc

    async def get_usage_document(self, user_id: str, period_key: str):
        return self.usage.get((user_id, period_key))

    async def increment_meter_if_under_limit(self, user_id, period_key, meter, limit):
        key = (user_id, period_key)
        doc = self.usage.setdefault(key, {"meters": {}})
        used = doc["meters"].get(meter, 0)
        if limit <= 0 or used >= limit:
            raise MeterLimitExceeded("limit")
        doc["meters"][meter] = used + 1
        return doc

    async def increment_meter_by_if_under_limit(
        self, user_id, period_key, meter, delta, limit
    ):
        key = (user_id, period_key)
        doc = self.usage.setdefault(key, {"meters": {}})
        used = int(doc["meters"].get(meter, 0))
        if delta <= 0 or limit < delta or used + delta > limit:
            raise MeterLimitExceeded("limit")
        doc["meters"][meter] = used + delta
        return doc

    async def decrement_meter_by(self, user_id, period_key, meter, delta) -> None:
        if delta <= 0:
            return
        key = (user_id, period_key)
        doc = self.usage.setdefault(key, {"meters": {}})
        used = int(doc["meters"].get(meter, 0))
        doc["meters"][meter] = max(0, used - delta)

    async def reserve_consumption(self, reservation_id, payload):
        if reservation_id in self.reservations:
            return False
        self.reservations[reservation_id] = payload
        return True

    async def get_reservation(self, reservation_id):
        return self.reservations.get(reservation_id)

    async def record_webhook_event(self, event_id, payload):
        if event_id in self.webhooks:
            return False
        self.webhooks.add(event_id)
        return True

    async def append_ledger_entry(self, user_id, entry):
        row = {"user_id": user_id, **entry}
        self.ledger.append(row)
        return row

    async def list_ledger(self, user_id, limit=50):
        return [e for e in self.ledger if e.get("user_id") == user_id][:limit]

    def set_plan(self, user_id: str, plan_id: str, status: str = "active") -> None:
        self.subscriptions[user_id] = {
            "user_id": user_id,
            "plan_id": plan_id,
            "status": status,
        }
