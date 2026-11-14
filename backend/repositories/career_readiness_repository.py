from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING
from pymongo.errors import PyMongoError

READINESS_REPORTS_COLLECTION = "career_readiness_reports"


class CareerReadinessRepositoryError(Exception):
    pass


class CareerReadinessRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db[READINESS_REPORTS_COLLECTION]
        self._indexes_ensured = False

    async def ensure_indexes(self) -> None:
        if self._indexes_ensured:
            return
        await self._collection.create_index(
            [("user_id", 1), ("generated_at", DESCENDING)],
            name="user_generated_at",
        )
        await self._collection.create_index(
            [("user_id", 1), ("resume_id", 1), ("job_match_id", 1)],
            name="user_resume_job_match",
        )
        self._indexes_ensured = True

    async def create_report(self, document: dict) -> dict:
        await self.ensure_indexes()
        now = datetime.now(timezone.utc)
        document.setdefault("generated_at", now)
        document.setdefault("created_at", now)
        try:
            result = await self._collection.insert_one(document)
        except PyMongoError:
            raise CareerReadinessRepositoryError("Failed to save readiness report") from None
        document["_id"] = result.inserted_id
        return document

    async def find_by_id_for_user(self, report_id: str, user_id: str) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(report_id)
        except (InvalidId, TypeError):
            return None
        return await self._collection.find_one({"_id": oid, "user_id": user_id})

    async def list_by_user(self, user_id: str, limit: int = 20) -> list[dict]:
        await self.ensure_indexes()
        cursor = (
            self._collection.find({"user_id": user_id})
            .sort("generated_at", DESCENDING)
            .limit(max(1, min(limit, 50)))
        )
        return await cursor.to_list(length=limit)
