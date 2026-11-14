from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING
from pymongo.errors import PyMongoError

JOB_MATCHES_COLLECTION = "job_matches"


class JobMatchRepositoryError(Exception):
    pass


class JobMatchRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db[JOB_MATCHES_COLLECTION]
        self._indexes_ensured = False

    async def ensure_indexes(self) -> None:
        if self._indexes_ensured:
            return
        await self._collection.create_index(
            [("user_id", 1), ("created_at", DESCENDING)],
            name="user_created_at",
        )
        await self._collection.create_index(
            [("user_id", 1), ("resume_id", 1), ("created_at", DESCENDING)],
            name="user_resume_created_at",
        )
        self._indexes_ensured = True

    async def create_match(self, document: dict) -> dict:
        await self.ensure_indexes()
        now = datetime.now(timezone.utc)
        document.setdefault("created_at", now)
        document.setdefault("updated_at", now)
        try:
            result = await self._collection.insert_one(document)
        except PyMongoError:
            raise JobMatchRepositoryError("Failed to save job match analysis") from None
        document["_id"] = result.inserted_id
        return document

    async def find_by_id_for_user(self, match_id: str, user_id: str) -> dict | None:
        await self.ensure_indexes()
        from bson import ObjectId
        from bson.errors import InvalidId

        try:
            oid = ObjectId(match_id)
        except (InvalidId, TypeError):
            return None
        return await self._collection.find_one({"_id": oid, "user_id": user_id})

    async def list_by_user(self, user_id: str, limit: int = 50) -> list[dict]:
        await self.ensure_indexes()
        cursor = self._collection.find({"user_id": user_id}).sort(
            "created_at", DESCENDING
        ).limit(max(1, min(limit, 100)))
        return await cursor.to_list(length=limit)
