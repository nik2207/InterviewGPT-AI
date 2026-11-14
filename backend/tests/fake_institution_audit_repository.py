from datetime import datetime, timezone

from bson import ObjectId


class FakeInstitutionAuditRepository:
    def __init__(self) -> None:
        self.entries: list[dict] = []

    async def ensure_indexes(self) -> None:
        return None

    async def append(
        self, institution_id: str, actor_user_id: str, action: str, *, detail=None
    ) -> None:
        self.entries.append(
            {
                "_id": ObjectId(),
                "institution_id": institution_id,
                "actor_user_id": actor_user_id,
                "action": action,
                "detail": detail or {},
                "created_at": datetime.now(timezone.utc),
            }
        )

    async def list_for_institution(self, institution_id: str, *, skip=0, limit=50):
        rows = [e for e in self.entries if e["institution_id"] == institution_id]
        rows.sort(key=lambda r: r["created_at"], reverse=True)
        total = len(rows)
        return rows[skip : skip + limit], total

    @staticmethod
    def oid_str(value) -> str:
        return str(value)
