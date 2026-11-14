from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING, ReturnDocument
from pymongo.errors import PyMongoError

GITHUB_PROFILE_CACHE_COLLECTION = "github_profile_cache"
GITHUB_REPO_ANALYSES_COLLECTION = "github_repo_analyses"


class GitHubAnalysisRepositoryError(Exception):
    pass


class GitHubAnalysisRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._cache = db[GITHUB_PROFILE_CACHE_COLLECTION]
        self._analyses = db[GITHUB_REPO_ANALYSES_COLLECTION]
        self._indexes_ensured = False

    async def ensure_indexes(self) -> None:
        if self._indexes_ensured:
            return
        await self._cache.create_index([("owner", 1)], name="owner", unique=True)
        await self._analyses.create_index(
            [("user_id", 1), ("created_at", DESCENDING)],
            name="user_created_at",
        )
        await self._analyses.create_index(
            [("user_id", 1), ("repo_full_name", 1)],
            name="user_repo",
        )
        self._indexes_ensured = True

    async def get_cached_profile(
        self, owner: str, max_age_minutes: int
    ) -> dict | None:
        await self.ensure_indexes()
        doc = await self._cache.find_one({"owner": owner.lower()})
        if doc is None:
            return None
        fetched_at = doc.get("fetched_at")
        if not isinstance(fetched_at, datetime):
            return None
        if fetched_at < datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes):
            return None
        return doc

    async def upsert_profile_cache(self, owner: str, payload: dict) -> None:
        await self.ensure_indexes()
        now = datetime.now(timezone.utc)
        try:
            await self._cache.update_one(
                {"owner": owner.lower()},
                {
                    "$set": {
                        **payload,
                        "owner": owner.lower(),
                        "fetched_at": now,
                        "updated_at": now,
                    }
                },
                upsert=True,
            )
        except PyMongoError:
            raise GitHubAnalysisRepositoryError("Failed to cache profile") from None

    async def create_analysis(self, document: dict) -> dict:
        await self.ensure_indexes()
        now = datetime.now(timezone.utc)
        document.setdefault("created_at", now)
        try:
            result = await self._analyses.insert_one(document)
        except PyMongoError:
            raise GitHubAnalysisRepositoryError("Failed to save analysis") from None
        document["_id"] = result.inserted_id
        return document

    async def find_analysis_for_user(self, analysis_id: str, user_id: str) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(analysis_id)
        except InvalidId:
            return None
        return await self._analyses.find_one({"_id": oid, "user_id": user_id})

    async def list_analyses_for_user(self, user_id: str, limit: int = 40) -> list[dict]:
        await self.ensure_indexes()
        cursor = (
            self._analyses.find({"user_id": user_id})
            .sort("created_at", DESCENDING)
            .limit(max(1, min(limit, 50)))
        )
        return await cursor.to_list(length=limit)
