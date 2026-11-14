from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError

ACCOUNTS_COLLECTION = "credit_accounts"
TRANSACTIONS_COLLECTION = "credit_transactions"
TOPUP_ORDERS_COLLECTION = "credit_topup_orders"


class CreditRepositoryError(Exception):
    pass


class InsufficientCredits(CreditRepositoryError):
    pass


class CreditRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._accounts = db[ACCOUNTS_COLLECTION]
        self._transactions = db[TRANSACTIONS_COLLECTION]
        self._topups = db[TOPUP_ORDERS_COLLECTION]
        self._indexes_ensured = False

    async def ensure_indexes(self) -> None:
        if self._indexes_ensured:
            return
        await self._accounts.create_index([("user_id", 1)], unique=True, name="credit_user")
        await self._transactions.create_index(
            [("idempotency_key", 1)], unique=True, name="credit_idem"
        )
        await self._transactions.create_index(
            [("user_id", 1), ("created_at", -1)], name="credit_user_tx"
        )
        await self._topups.create_index(
            [("idempotency_key", 1)], unique=True, name="topup_idem"
        )
        self._indexes_ensured = True

    async def get_account(self, user_id: str) -> dict | None:
        await self.ensure_indexes()
        return await self._accounts.find_one({"user_id": user_id})

    async def ensure_account(self, user_id: str) -> dict:
        await self.ensure_indexes()
        now = datetime.now(timezone.utc)
        doc = await self._accounts.find_one_and_update(
            {"user_id": user_id},
            {
                "$setOnInsert": {
                    "user_id": user_id,
                    "purchased_balance": 0,
                    "purchased_lots": [],
                    "created_at": now,
                },
                "$set": {"updated_at": now},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if doc is None:
            raise CreditRepositoryError("Unable to load credit account")
        return doc

    async def get_transaction_by_idempotency(self, idempotency_key: str) -> dict | None:
        await self.ensure_indexes()
        return await self._transactions.find_one({"idempotency_key": idempotency_key})

    async def insert_transaction(self, document: dict) -> dict:
        await self.ensure_indexes()
        document.setdefault("created_at", datetime.now(timezone.utc))
        try:
            result = await self._transactions.insert_one(document)
        except DuplicateKeyError:
            raise CreditRepositoryError("duplicate_idempotency") from None
        except PyMongoError as exc:
            raise CreditRepositoryError("transaction_insert_failed") from exc
        document["_id"] = result.inserted_id
        return document

    async def mark_transaction_refunded(self, idempotency_key: str, refund_key: str) -> dict | None:
        await self.ensure_indexes()
        now = datetime.now(timezone.utc)
        return await self._transactions.find_one_and_update(
            {"idempotency_key": idempotency_key, "status": "committed"},
            {
                "$set": {
                    "status": "refunded",
                    "refund_idempotency_key": refund_key,
                    "refunded_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )

    async def debit_purchased(self, user_id: str, amount: int) -> dict:
        await self.ensure_indexes()
        if amount <= 0:
            raise CreditRepositoryError("invalid_amount")
        updated = await self._accounts.find_one_and_update(
            {"user_id": user_id, "purchased_balance": {"$gte": amount}},
            {
                "$inc": {"purchased_balance": -amount},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
            return_document=ReturnDocument.AFTER,
        )
        if updated is None:
            raise InsufficientCredits("Insufficient purchased credits")
        return updated

    async def credit_purchased(
        self,
        user_id: str,
        amount: int,
        *,
        expires_at: datetime | None,
    ) -> dict:
        await self.ensure_indexes()
        await self.ensure_account(user_id)
        lot = {
            "credits_remaining": amount,
            "credits_original": amount,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc),
        }
        updated = await self._accounts.find_one_and_update(
            {"user_id": user_id},
            {
                "$inc": {"purchased_balance": amount},
                "$push": {"purchased_lots": lot},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
            return_document=ReturnDocument.AFTER,
        )
        if updated is None:
            raise CreditRepositoryError("credit_topup_failed")
        return updated

    async def refund_purchased(self, user_id: str, amount: int) -> dict:
        await self.ensure_indexes()
        return await self._accounts.find_one_and_update(
            {"user_id": user_id},
            {
                "$inc": {"purchased_balance": amount},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
            return_document=ReturnDocument.AFTER,
        )

    async def list_transactions(self, user_id: str, limit: int = 50) -> list[dict]:
        await self.ensure_indexes()
        cursor = (
            self._transactions.find({"user_id": user_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def record_topup_order(self, idempotency_key: str, payload: dict) -> bool:
        await self.ensure_indexes()
        doc = {
            "idempotency_key": idempotency_key,
            "created_at": datetime.now(timezone.utc),
            **payload,
        }
        try:
            await self._topups.insert_one(doc)
            return True
        except DuplicateKeyError:
            return False

    async def get_topup_order(self, idempotency_key: str) -> dict | None:
        await self.ensure_indexes()
        return await self._topups.find_one({"idempotency_key": idempotency_key})

    @staticmethod
    def oid_str(value) -> str:
        if isinstance(value, ObjectId):
            return str(value)
        return str(value)
