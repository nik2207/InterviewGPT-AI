from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError

JOB_APPLICATIONS_COLLECTION = "job_applications"


class JobApplicationRepositoryError(Exception):
    pass


class JobApplicationDuplicateError(JobApplicationRepositoryError):
    pass


def _duplicate_key(company: str, job_title: str, job_posting_url: str | None) -> str:
    url = (job_posting_url or "").strip().lower()
    return "|".join([company.strip().lower(), job_title.strip().lower(), url])


class JobApplicationRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db[JOB_APPLICATIONS_COLLECTION]
        self._indexes_ensured = False

    async def ensure_indexes(self) -> None:
        if self._indexes_ensured:
            return
        await self._collection.create_index(
            [("user_id", 1), ("created_at", DESCENDING)],
            name="user_created_at",
        )
        await self._collection.create_index(
            [("user_id", 1), ("status", 1)],
            name="user_status",
        )
        await self._collection.create_index(
            [("user_id", 1), ("duplicate_key", 1)],
            name="user_duplicate_key",
            unique=True,
        )
        await self._collection.create_index(
            [("user_id", 1), ("follow_up_date", ASCENDING)],
            name="user_follow_up",
        )
        self._indexes_ensured = True

    async def create_application(self, document: dict) -> dict:
        await self.ensure_indexes()
        now = datetime.now(timezone.utc)
        document.setdefault("created_at", now)
        document.setdefault("updated_at", now)
        document["duplicate_key"] = _duplicate_key(
            document["company"],
            document["job_title"],
            document.get("job_posting_url"),
        )
        try:
            result = await self._collection.insert_one(document)
        except DuplicateKeyError:
            raise JobApplicationDuplicateError(
                "An application with this company, title, and URL already exists."
            ) from None
        except PyMongoError:
            raise JobApplicationRepositoryError("Failed to create application") from None
        document["_id"] = result.inserted_id
        return document

    async def find_by_id_for_user(self, app_id: str, user_id: str) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(app_id)
        except InvalidId:
            return None
        return await self._collection.find_one({"_id": oid, "user_id": user_id})

    async def update_application(
        self,
        app_id: str,
        user_id: str,
        update_fields: dict,
    ) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(app_id)
        except InvalidId:
            return None

        if "company" in update_fields or "job_title" in update_fields or "job_posting_url" in update_fields:
            existing = await self.find_by_id_for_user(app_id, user_id)
            if existing is None:
                return None
            company = update_fields.get("company", existing["company"])
            title = update_fields.get("job_title", existing["job_title"])
            url = update_fields.get("job_posting_url", existing.get("job_posting_url"))
            update_fields["duplicate_key"] = _duplicate_key(company, title, url)

        update_fields["updated_at"] = datetime.now(timezone.utc)
        try:
            return await self._collection.find_one_and_update(
                {"_id": oid, "user_id": user_id},
                {"$set": update_fields},
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            raise JobApplicationDuplicateError(
                "Update would duplicate another application."
            ) from None
        except PyMongoError:
            raise JobApplicationRepositoryError("Failed to update application") from None

    async def delete_application(self, app_id: str, user_id: str) -> bool:
        await self.ensure_indexes()
        try:
            oid = ObjectId(app_id)
        except InvalidId:
            return False
        try:
            result = await self._collection.delete_one({"_id": oid, "user_id": user_id})
        except PyMongoError:
            raise JobApplicationRepositoryError("Failed to delete application") from None
        return result.deleted_count == 1

    async def list_applications(
        self,
        user_id: str,
        *,
        status: str | None,
        search: str | None,
        employment_type: str | None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_dir: int,
    ) -> tuple[list[dict], int]:
        await self.ensure_indexes()
        query: dict = {"user_id": user_id}
        if status:
            query["status"] = status
        if employment_type:
            query["employment_type"] = employment_type
        if search and search.strip():
            pattern = search.strip()
            query["$or"] = [
                {"company": {"$regex": pattern, "$options": "i"}},
                {"job_title": {"$regex": pattern, "$options": "i"}},
                {"location": {"$regex": pattern, "$options": "i"}},
            ]

        total = await self._collection.count_documents(query)
        skip = max(0, (page - 1) * page_size)
        allowed_sort = {
            "created_at",
            "updated_at",
            "application_date",
            "follow_up_date",
            "company",
            "status",
        }
        field = sort_by if sort_by in allowed_sort else "updated_at"
        direction = DESCENDING if sort_dir < 0 else ASCENDING

        cursor = (
            self._collection.find(query)
            .sort(field, direction)
            .skip(skip)
            .limit(max(1, min(page_size, 100)))
        )
        items = await cursor.to_list(length=page_size)
        return items, total

    async def list_all_for_user(self, user_id: str, limit: int = 500) -> list[dict]:
        await self.ensure_indexes()
        cursor = (
            self._collection.find({"user_id": user_id})
            .sort("updated_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def link_interview_session(
        self, app_id: str, user_id: str, session_id: str
    ) -> dict | None:
        return await self.update_application(
            app_id,
            user_id,
            {"interview_session_id": session_id},
        )
