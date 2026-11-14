import threading
from datetime import datetime, timezone

from bson import ObjectId

from repositories.credit_repository import CreditRepositoryError, InsufficientCredits


class FakeCreditRepository:
    """In-memory credit store for API tests."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.accounts: dict[str, dict] = {}
        self.transactions: dict[str, dict] = {}
        self.topups: dict[str, dict] = {}
        self._indexes_ensured = True

    async def ensure_indexes(self) -> None:
        return None

    async def get_account(self, user_id: str) -> dict | None:
        return self.accounts.get(user_id)

    def _ensure_account_unlocked(self, user_id: str) -> dict:
        doc = self.accounts.get(user_id)
        if doc is None:
            now = datetime.now(timezone.utc)
            doc = {
                "user_id": user_id,
                "purchased_balance": 0,
                "purchased_lots": [],
                "created_at": now,
                "updated_at": now,
            }
            self.accounts[user_id] = doc
        return doc

    async def ensure_account(self, user_id: str) -> dict:
        with self._lock:
            return dict(self._ensure_account_unlocked(user_id))

    async def get_transaction_by_idempotency(self, idempotency_key: str) -> dict | None:
        return self.transactions.get(idempotency_key)

    async def insert_transaction(self, document: dict) -> dict:
        key = document["idempotency_key"]
        with self._lock:
            if key in self.transactions:
                raise CreditRepositoryError("duplicate_idempotency")
            doc = {
                **document,
                "_id": ObjectId(),
                "created_at": document.get("created_at", datetime.now(timezone.utc)),
            }
            self.transactions[key] = doc
            return dict(doc)

    async def mark_transaction_refunded(self, idempotency_key: str, refund_key: str) -> dict | None:
        with self._lock:
            txn = self.transactions.get(idempotency_key)
            if txn is None or txn.get("status") != "committed":
                return None
            txn = {**txn, "status": "refunded", "refund_idempotency_key": refund_key}
            self.transactions[idempotency_key] = txn
            return dict(txn)

    async def debit_purchased(self, user_id: str, amount: int) -> dict:
        with self._lock:
            account = self.accounts.setdefault(
                user_id,
                {
                    "user_id": user_id,
                    "purchased_balance": 0,
                    "purchased_lots": [],
                },
            )
            balance = int(account.get("purchased_balance", 0))
            if balance < amount:
                raise InsufficientCredits("Insufficient purchased credits")
            account["purchased_balance"] = balance - amount
            return dict(account)

    async def credit_purchased(
        self, user_id: str, amount: int, *, expires_at: datetime | None
    ) -> dict:
        with self._lock:
            account = self._ensure_account_unlocked(user_id)
            account["purchased_balance"] = int(account.get("purchased_balance", 0)) + amount
            lots = list(account.get("purchased_lots") or [])
            lots.append(
                {
                    "credits_remaining": amount,
                    "credits_original": amount,
                    "expires_at": expires_at,
                    "created_at": datetime.now(timezone.utc),
                }
            )
            account["purchased_lots"] = lots
            self.accounts[user_id] = account
            return dict(account)

    async def refund_purchased(self, user_id: str, amount: int) -> dict:
        with self._lock:
            account = self._ensure_account_unlocked(user_id)
            account["purchased_balance"] = int(account.get("purchased_balance", 0)) + amount
            self.accounts[user_id] = account
            return dict(account)

    async def list_transactions(self, user_id: str, limit: int = 50) -> list[dict]:
        rows = [t for t in self.transactions.values() if t.get("user_id") == user_id]
        rows.sort(key=lambda r: r.get("created_at", datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        return rows[:limit]

    async def record_topup_order(self, idempotency_key: str, payload: dict) -> bool:
        with self._lock:
            if idempotency_key in self.topups:
                return False
            self.topups[idempotency_key] = {
                "idempotency_key": idempotency_key,
                **payload,
            }
            return True

    async def get_topup_order(self, idempotency_key: str) -> dict | None:
        return self.topups.get(idempotency_key)

    @staticmethod
    def oid_str(value) -> str:
        if isinstance(value, ObjectId):
            return str(value)
        return str(value)

    def add_purchased_balance(self, user_id: str, amount: int) -> None:
        account = self.accounts.setdefault(
            user_id,
            {"user_id": user_id, "purchased_balance": 0, "purchased_lots": []},
        )
        account["purchased_balance"] = int(account.get("purchased_balance", 0)) + amount
