from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING, ReturnDocument
from pymongo.errors import PyMongoError

PREPARATION_PLANS_COLLECTION = "preparation_plans"


class PreparationPlanRepositoryError(Exception):
    pass


class PreparationPlanRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db[PREPARATION_PLANS_COLLECTION]
        self._indexes_ensured = False

    async def ensure_indexes(self) -> None:
        if self._indexes_ensured:
            return
        await self._collection.create_index(
            [("user_id", 1), ("status", 1), ("created_at", DESCENDING)],
            name="user_status_created_at",
        )
        await self._collection.create_index(
            [("user_id", 1), ("resume_id", 1)],
            name="user_resume",
        )
        self._indexes_ensured = True

    async def create_plan(self, document: dict) -> dict:
        await self.ensure_indexes()
        now = datetime.now(timezone.utc)
        document.setdefault("created_at", now)
        document.setdefault("updated_at", now)
        try:
            result = await self._collection.insert_one(document)
        except PyMongoError:
            raise PreparationPlanRepositoryError("Failed to save preparation plan") from None
        document["_id"] = result.inserted_id
        return document

    async def find_by_id_for_user(self, plan_id: str, user_id: str) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(plan_id)
        except (InvalidId, TypeError):
            return None
        return await self._collection.find_one({"_id": oid, "user_id": user_id})

    async def list_by_user(self, user_id: str, limit: int = 20) -> list[dict]:
        await self.ensure_indexes()
        cursor = (
            self._collection.find({"user_id": user_id})
            .sort("created_at", DESCENDING)
            .limit(max(1, min(limit, 50)))
        )
        return await cursor.to_list(length=limit)

    async def archive_plan(self, plan_id: str, user_id: str) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(plan_id)
        except (InvalidId, TypeError):
            return None
        now = datetime.now(timezone.utc)
        return await self._collection.find_one_and_update(
            {"_id": oid, "user_id": user_id, "status": "active"},
            {"$set": {"status": "archived", "updated_at": now, "archived_at": now}},
            return_document=ReturnDocument.AFTER,
        )

    async def update_task_completion(
        self,
        plan_id: str,
        user_id: str,
        day_number: int,
        task_id: str,
        completed: bool,
    ) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(plan_id)
        except (InvalidId, TypeError):
            return None

        now = datetime.now(timezone.utc)
        plan = await self.find_by_id_for_user(plan_id, user_id)
        if plan is None:
            return None

        days = plan.get("days") or []
        updated = False
        for day in days:
            if day.get("day_number") != day_number:
                continue
            for task in day.get("tasks") or []:
                if task.get("task_id") != task_id:
                    continue
                task["completed"] = completed
                task["completed_at"] = now if completed else None
                updated = True
            if updated:
                tasks = day.get("tasks") or []
                day["day_completed"] = tasks and all(t.get("completed") for t in tasks)
            break

        if not updated:
            return None

        try:
            return await self._collection.find_one_and_update(
                {"_id": oid, "user_id": user_id},
                {"$set": {"days": days, "updated_at": now}},
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError:
            raise PreparationPlanRepositoryError("Failed to update task") from None
