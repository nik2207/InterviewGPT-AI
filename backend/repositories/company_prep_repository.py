from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING, ReturnDocument
from pymongo.errors import PyMongoError

COMPANY_PREP_COLLECTION = "company_preparations"


class CompanyPrepRepositoryError(Exception):
    pass


class CompanyPrepRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db[COMPANY_PREP_COLLECTION]
        self._indexes_ensured = False

    async def ensure_indexes(self) -> None:
        if self._indexes_ensured:
            return
        await self._collection.create_index(
            [("user_id", 1), ("created_at", DESCENDING)],
            name="user_created_at",
        )
        await self._collection.create_index(
            [("user_id", 1), ("company_id", 1)],
            name="user_company",
        )
        self._indexes_ensured = True

    async def create_prep(self, document: dict) -> dict:
        await self.ensure_indexes()
        now = datetime.now(timezone.utc)
        document.setdefault("created_at", now)
        document.setdefault("updated_at", now)
        try:
            result = await self._collection.insert_one(document)
        except PyMongoError:
            raise CompanyPrepRepositoryError("Failed to save preparation") from None
        document["_id"] = result.inserted_id
        return document

    async def find_by_id_for_user(self, prep_id: str, user_id: str) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(prep_id)
        except InvalidId:
            return None
        return await self._collection.find_one({"_id": oid, "user_id": user_id})

    async def list_by_user(self, user_id: str, limit: int = 30) -> list[dict]:
        await self.ensure_indexes()
        cursor = (
            self._collection.find({"user_id": user_id})
            .sort("created_at", DESCENDING)
            .limit(max(1, min(limit, 50)))
        )
        return await cursor.to_list(length=limit)

    async def update_checklist(
        self,
        prep_id: str,
        user_id: str,
        checklist: list[dict],
    ) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(prep_id)
        except InvalidId:
            return None
        now = datetime.now(timezone.utc)
        try:
            return await self._collection.find_one_and_update(
                {"_id": oid, "user_id": user_id},
                {"$set": {"checklist": checklist, "updated_at": now}},
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError:
            raise CompanyPrepRepositoryError("Failed to update checklist") from None

    async def link_interview_session(
        self,
        prep_id: str,
        user_id: str,
        interview_session_id: str,
    ) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(prep_id)
        except InvalidId:
            return None
        now = datetime.now(timezone.utc)
        try:
            return await self._collection.find_one_and_update(
                {"_id": oid, "user_id": user_id},
                {
                    "$set": {
                        "interview_session_id": interview_session_id,
                        "updated_at": now,
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError:
            raise CompanyPrepRepositoryError("Failed to link interview") from None
