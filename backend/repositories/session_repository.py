from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

REVOKED_TOKENS_COLLECTION = "revoked_tokens"


class SessionRepository:
    """Tracks revoked application JWTs (by jti) until they expire."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db[REVOKED_TOKENS_COLLECTION]
        self._indexes_ensured = False

    async def ensure_indexes(self) -> None:
        if self._indexes_ensured:
            return
        await self._collection.create_index("jti", unique=True, name="jti_unique")
        await self._collection.create_index(
            "expires_at",
            expireAfterSeconds=0,
            name="expires_at_ttl",
        )
        self._indexes_ensured = True

    async def revoke_jti(self, jti: str, expires_at: datetime) -> None:
        await self.ensure_indexes()
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        await self._collection.update_one(
            {"jti": jti},
            {
                "$set": {
                    "jti": jti,
                    "expires_at": expires_at,
                    "revoked_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )

    async def is_revoked(self, jti: str) -> bool:
        await self.ensure_indexes()
        document = await self._collection.find_one({"jti": jti}, {"_id": 1})
        return document is not None
