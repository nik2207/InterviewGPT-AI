from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError

SUBSCRIPTIONS_COLLECTION = "billing_subscriptions"
USAGE_COLLECTION = "billing_usage"
WEBHOOK_EVENTS_COLLECTION = "billing_webhook_events"
BILLING_LEDGER_COLLECTION = "billing_ledger"
CONSUMPTION_RESERVATIONS_COLLECTION = "billing_consumption_reservations"


class BillingRepositoryError(Exception):
    pass


class MeterLimitExceeded(BillingRepositoryError):
    pass


class BillingRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._subs = db[SUBSCRIPTIONS_COLLECTION]
        self._usage = db[USAGE_COLLECTION]
        self._webhooks = db[WEBHOOK_EVENTS_COLLECTION]
        self._ledger = db[BILLING_LEDGER_COLLECTION]
        self._reservations = db[CONSUMPTION_RESERVATIONS_COLLECTION]
        self._users = db["users"]
        self._indexes_ensured = False

    async def ensure_indexes(self) -> None:
        if self._indexes_ensured:
            return
        await self._subs.create_index([("user_id", 1)], unique=True, name="user_sub_unique")
        await self._subs.create_index(
            [("razorpay_subscription_id", 1)],
            unique=True,
            sparse=True,
            name="razorpay_sub_id",
        )
        await self._usage.create_index(
            [("user_id", 1), ("period_key", 1)],
            unique=True,
            name="user_period",
        )
        await self._webhooks.create_index([("event_id", 1)], unique=True, name="event_id_unique")
        await self._ledger.create_index([("user_id", 1), ("created_at", -1)], name="user_ledger")
        await self._reservations.create_index(
            [("reservation_id", 1)], unique=True, name="reservation_unique"
        )
        self._indexes_ensured = True

    async def get_subscription_for_user(self, user_id: str) -> dict | None:
        await self.ensure_indexes()
        return await self._subs.find_one({"user_id": user_id})

    async def get_user_trial(self, user_id: str) -> dict | None:
        """Read trial dates, granting legacy accounts a one-time rollout trial."""
        users_collection = getattr(self, "_users", None)
        if users_collection is None:
            return None
        try:
            object_id = ObjectId(user_id)
        except InvalidId:
            return None
        projection = {"trial_ends_at": 1, "created_at": 1}
        now = datetime.now(timezone.utc)
        document = await users_collection.find_one_and_update(
            {
                "_id": object_id,
                "$or": [
                    {"trial_ends_at": {"$exists": False}},
                    {"trial_ends_at": None},
                ],
            },
            {"$set": {"trial_ends_at": now + timedelta(days=7)}},
            projection=projection,
            return_document=ReturnDocument.AFTER,
        )
        if document is not None:
            return document
        return await users_collection.find_one({"_id": object_id}, projection)

    async def get_subscription_by_razorpay_id(self, razorpay_subscription_id: str) -> dict | None:
        await self.ensure_indexes()
        return await self._subs.find_one(
            {"razorpay_subscription_id": razorpay_subscription_id}
        )

    async def upsert_subscription(self, user_id: str, fields: dict) -> dict:
        await self.ensure_indexes()
        now = datetime.now(timezone.utc)
        fields.setdefault("updated_at", now)
        fields["user_id"] = user_id
        doc = await self._subs.find_one_and_update(
            {"user_id": user_id},
            {
                "$set": fields,
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if doc is None:
            raise BillingRepositoryError("Failed to save subscription")
        return doc

    async def get_usage_document(self, user_id: str, period_key: str) -> dict | None:
        await self.ensure_indexes()
        return await self._usage.find_one({"user_id": user_id, "period_key": period_key})

    async def increment_meter_if_under_limit(
        self,
        user_id: str,
        period_key: str,
        meter: str,
        limit: int,
    ) -> dict:
        await self.ensure_indexes()
        if limit <= 0:
            raise MeterLimitExceeded(f"Meter {meter} not included in plan")

        filter_doc = {
            "user_id": user_id,
            "period_key": period_key,
            "$or": [
                {f"meters.{meter}": {"$exists": False}},
                {f"meters.{meter}": {"$lt": limit}},
            ],
        }
        try:
            updated = await self._usage.find_one_and_update(
                filter_doc,
                {
                    "$inc": {f"meters.{meter}": 1},
                    "$setOnInsert": {
                        "user_id": user_id,
                        "period_key": period_key,
                        "created_at": datetime.now(timezone.utc),
                    },
                    "$set": {"updated_at": datetime.now(timezone.utc)},
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            raise MeterLimitExceeded("Usage limit reached") from None
        except PyMongoError as exc:
            raise BillingRepositoryError("Usage update failed") from exc

        if updated is None:
            raise MeterLimitExceeded("Usage limit reached")
        used = (updated.get("meters") or {}).get(meter, 0)
        if used > limit:
            await self._usage.update_one(
                {"user_id": user_id, "period_key": period_key},
                {"$inc": {f"meters.{meter}": -1}},
            )
            raise MeterLimitExceeded("Usage limit reached")
        return updated

    async def increment_meter_by_if_under_limit(
        self,
        user_id: str,
        period_key: str,
        meter: str,
        delta: int,
        limit: int,
    ) -> dict:
        await self.ensure_indexes()
        if delta <= 0:
            raise MeterLimitExceeded("Invalid meter delta")
        if limit < delta:
            raise MeterLimitExceeded(f"Meter {meter} limit too low")

        existing = await self.get_usage_document(user_id, period_key)
        used = int((existing or {}).get("meters", {}).get(meter, 0))
        if used + delta > limit:
            raise MeterLimitExceeded("Usage limit reached")

        try:
            updated = await self._usage.find_one_and_update(
                {"user_id": user_id, "period_key": period_key},
                {
                    "$inc": {f"meters.{meter}": delta},
                    "$setOnInsert": {
                        "user_id": user_id,
                        "period_key": period_key,
                        "created_at": datetime.now(timezone.utc),
                    },
                    "$set": {"updated_at": datetime.now(timezone.utc)},
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError as exc:
            raise BillingRepositoryError("Usage update failed") from exc

        if updated is None:
            raise MeterLimitExceeded("Usage limit reached")
        new_used = int((updated.get("meters") or {}).get(meter, 0))
        if new_used > limit:
            await self._usage.update_one(
                {"user_id": user_id, "period_key": period_key},
                {"$inc": {f"meters.{meter}": -delta}},
            )
            raise MeterLimitExceeded("Usage limit reached")
        return updated

    async def decrement_meter_by(
        self,
        user_id: str,
        period_key: str,
        meter: str,
        delta: int,
    ) -> None:
        await self.ensure_indexes()
        if delta <= 0:
            return
        await self._usage.update_one(
            {"user_id": user_id, "period_key": period_key},
            {"$inc": {f"meters.{meter}": -delta}},
        )

    async def reserve_consumption(self, reservation_id: str, payload: dict) -> bool:
        await self.ensure_indexes()
        doc = {
            "reservation_id": reservation_id,
            "created_at": datetime.now(timezone.utc),
            **payload,
        }
        try:
            await self._reservations.insert_one(doc)
            return True
        except DuplicateKeyError:
            return False

    async def get_reservation(self, reservation_id: str) -> dict | None:
        await self.ensure_indexes()
        return await self._reservations.find_one({"reservation_id": reservation_id})

    async def record_webhook_event(self, event_id: str, payload: dict) -> bool:
        """Returns True if newly recorded, False if duplicate."""
        await self.ensure_indexes()
        doc = {
            "event_id": event_id,
            "payload": payload,
            "processed_at": datetime.now(timezone.utc),
        }
        try:
            await self._webhooks.insert_one(doc)
            return True
        except DuplicateKeyError:
            return False

    async def append_ledger_entry(self, user_id: str, entry: dict) -> dict:
        await self.ensure_indexes()
        now = datetime.now(timezone.utc)
        document = {
            "user_id": user_id,
            "created_at": now,
            **entry,
        }
        result = await self._ledger.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def list_ledger(self, user_id: str, limit: int = 50) -> list[dict]:
        await self.ensure_indexes()
        cursor = self._ledger.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def find_ledger_by_id(self, ledger_id: str, user_id: str) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(ledger_id)
        except InvalidId:
            return None
        return await self._ledger.find_one({"_id": oid, "user_id": user_id})
