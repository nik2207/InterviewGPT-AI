from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING
from pymongo.errors import PyMongoError

RESUMES_COLLECTION = "resumes"


class ResumeRepositoryError(Exception):
    """Raised when resume persistence fails."""


class ResumeRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db[RESUMES_COLLECTION]
        self._indexes_ensured = False

    async def ensure_indexes(self) -> None:
        if self._indexes_ensured:
            return
        await self._collection.create_index(
            [("user_id", 1), ("uploaded_at", DESCENDING)],
            name="user_uploaded_at",
        )
        await self._collection.create_index(
            [("user_id", 1), ("content_sha256", 1)],
            name="user_content_sha256",
        )
        self._indexes_ensured = True

    async def create_resume(
        self,
        user_id: str,
        original_filename: str,
        file_size_bytes: int,
        extracted_text: str,
        page_count: int,
        content_sha256: str,
        parsing_status: str = "parsed",
    ) -> dict:
        await self.ensure_indexes()
        now = datetime.now(timezone.utc)
        document = {
            "user_id": user_id,
            "original_filename": original_filename,
            "file_size_bytes": file_size_bytes,
            "uploaded_at": now,
            "extracted_text": extracted_text,
            "page_count": page_count,
            "parsing_status": parsing_status,
            "content_sha256": content_sha256,
        }
        try:
            result = await self._collection.insert_one(document)
        except PyMongoError:
            raise ResumeRepositoryError("Failed to save resume") from None

        document["_id"] = result.inserted_id
        return document

    async def list_by_user(self, user_id: str, limit: int = 50) -> list[dict]:
        await self.ensure_indexes()
        cursor = (
            self._collection.find({"user_id": user_id})
            .sort("uploaded_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def find_by_id_for_user(self, resume_id: str, user_id: str) -> dict | None:
        from bson import ObjectId
        from bson.errors import InvalidId

        try:
            oid = ObjectId(resume_id)
        except InvalidId:
            return None

        return await self._collection.find_one({"_id": oid, "user_id": user_id})
