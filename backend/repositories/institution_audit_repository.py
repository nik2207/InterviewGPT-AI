from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

AUDIT_COLLECTION = "institution_audit_log"


class InstitutionAuditRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db[AUDIT_COLLECTION]
        self._indexes_ensured = False

    async def ensure_indexes(self) -> None:
        if self._indexes_ensured:
            return
        await self._collection.create_index(
            [("institution_id", 1), ("created_at", -1)],
            name="inst_audit_time",
        )
        self._indexes_ensured = True

    async def append(
        self,
        institution_id: str,
        actor_user_id: str,
        action: str,
        *,
        detail: dict | None = None,
    ) -> None:
        await self.ensure_indexes()
        await self._collection.insert_one(
            {
                "institution_id": institution_id,
                "actor_user_id": actor_user_id,
                "action": action,
                "detail": detail or {},
                "created_at": datetime.now(timezone.utc),
            }
        )

    async def list_for_institution(
        self, institution_id: str, *, skip: int = 0, limit: int = 50
    ) -> tuple[list[dict], int]:
        await self.ensure_indexes()
        query = {"institution_id": institution_id}
        total = await self._collection.count_documents(query)
        cursor = (
            self._collection.find(query)
            .sort("created_at", -1)
            .skip(max(0, skip))
            .limit(min(max(limit, 1), 100))
        )
        rows = await cursor.to_list(length=limit)
        return rows, total

    @staticmethod
    def oid_str(value) -> str:
        if isinstance(value, ObjectId):
            return str(value)
        return str(value)
