from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING, ReturnDocument
from pymongo.errors import PyMongoError

RESUME_BUILDER_COLLECTION = "resume_builder_documents"


class ResumeBuilderRepositoryError(Exception):
    pass


class ResumeBuilderRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db[RESUME_BUILDER_COLLECTION]
        self._indexes_ensured = False

    async def ensure_indexes(self) -> None:
        if self._indexes_ensured:
            return
        await self._collection.create_index(
            [("user_id", 1), ("updated_at", DESCENDING)],
            name="user_updated_at",
        )
        self._indexes_ensured = True

    async def create_document(self, document: dict) -> dict:
        await self.ensure_indexes()
        now = datetime.now(timezone.utc)
        document.setdefault("created_at", now)
        document.setdefault("updated_at", now)
        try:
            result = await self._collection.insert_one(document)
        except PyMongoError:
            raise ResumeBuilderRepositoryError("Failed to create resume builder") from None
        document["_id"] = result.inserted_id
        return document

    async def find_by_id_for_user(self, doc_id: str, user_id: str) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(doc_id)
        except InvalidId:
            return None
        return await self._collection.find_one({"_id": oid, "user_id": user_id})

    async def list_by_user(self, user_id: str, limit: int = 30) -> list[dict]:
        await self.ensure_indexes()
        cursor = (
            self._collection.find({"user_id": user_id})
            .sort("updated_at", DESCENDING)
            .limit(max(1, min(limit, 50)))
        )
        return await cursor.to_list(length=limit)

    async def update_document(
        self,
        doc_id: str,
        user_id: str,
        update_fields: dict,
    ) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(doc_id)
        except InvalidId:
            return None
        now = datetime.now(timezone.utc)
        update_fields["updated_at"] = now
        try:
            return await self._collection.find_one_and_update(
                {"_id": oid, "user_id": user_id},
                {"$set": update_fields},
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError:
            raise ResumeBuilderRepositoryError("Failed to update resume builder") from None

    async def append_version(
        self,
        doc_id: str,
        user_id: str,
        version: dict,
        max_versions: int = 25,
    ) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(doc_id)
        except InvalidId:
            return None

        doc = await self._collection.find_one({"_id": oid, "user_id": user_id})
        if doc is None:
            return None

        versions = list(doc.get("versions", []))
        versions.append(version)
        versions = versions[-max_versions:]
        now = datetime.now(timezone.utc)
        try:
            return await self._collection.find_one_and_update(
                {"_id": oid, "user_id": user_id},
                {"$set": {"versions": versions, "updated_at": now}},
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError:
            raise ResumeBuilderRepositoryError("Failed to save version") from None

    async def delete_document(self, doc_id: str, user_id: str) -> bool:
        await self.ensure_indexes()
        try:
            oid = ObjectId(doc_id)
        except InvalidId:
            return False
        try:
            result = await self._collection.delete_one({"_id": oid, "user_id": user_id})
        except PyMongoError:
            raise ResumeBuilderRepositoryError("Failed to delete resume builder") from None
        return result.deleted_count == 1
