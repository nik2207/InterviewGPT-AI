from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING
from pymongo.errors import PyMongoError

ANALYSES_COLLECTION = "resume_analyses"


class AnalysisRepositoryError(Exception):
    """Raised when analysis persistence fails."""


class AnalysisRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db[ANALYSES_COLLECTION]
        self._indexes_ensured = False

    async def ensure_indexes(self) -> None:
        if self._indexes_ensured:
            return
        await self._collection.create_index(
            [("user_id", 1), ("resume_id", 1), ("created_at", DESCENDING)],
            name="user_resume_created_at",
        )
        self._indexes_ensured = True

    async def find_latest_for_resume(
        self,
        user_id: str,
        resume_id: str,
    ) -> dict | None:
        await self.ensure_indexes()
        return await self._collection.find_one(
            {"user_id": user_id, "resume_id": resume_id, "status": "completed"},
            sort=[("created_at", DESCENDING)],
        )

    async def find_latest_matching_content(
        self,
        user_id: str,
        resume_id: str,
        content_sha256: str,
    ) -> dict | None:
        await self.ensure_indexes()
        return await self._collection.find_one(
            {
                "user_id": user_id,
                "resume_id": resume_id,
                "content_sha256": content_sha256,
                "status": "completed",
            },
            sort=[("created_at", DESCENDING)],
        )

    async def create_analysis(
        self,
        user_id: str,
        resume_id: str,
        content_sha256: str,
        model: str,
        analysis: dict,
        interview_questions: list[dict],
        status: str = "completed",
    ) -> dict:
        await self.ensure_indexes()
        now = datetime.now(timezone.utc)
        document = {
            "user_id": user_id,
            "resume_id": resume_id,
            "content_sha256": content_sha256,
            "model": model,
            "status": status,
            "analysis": analysis,
            "interview_questions": interview_questions,
            "created_at": now,
            "updated_at": now,
        }
        try:
            result = await self._collection.insert_one(document)
        except PyMongoError:
            raise AnalysisRepositoryError("Failed to save analysis") from None

        document["_id"] = result.inserted_id
        return document
