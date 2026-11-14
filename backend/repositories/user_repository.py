from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

USERS_COLLECTION = "users"


class UserRepositoryError(Exception):
    """Raised when user persistence fails unexpectedly."""


class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db[USERS_COLLECTION]
        self._indexes_ensured = False

    async def ensure_indexes(self) -> None:
        if self._indexes_ensured:
            return
        await self._collection.create_index(
            [("provider", 1), ("provider_id", 1)],
            unique=True,
            name="provider_provider_id_unique",
        )
        self._indexes_ensured = True

    async def find_by_google_sub(self, google_sub: str) -> dict | None:
        return await self._collection.find_one(
            {"provider": "google", "provider_id": google_sub}
        )

    async def upsert_google_user(
        self,
        google_sub: str,
        email: str,
        name: str,
        picture: str,
    ) -> dict:
        await self.ensure_indexes()

        now = datetime.now(timezone.utc)
        update = {
            "$set": {
                "email": email,
                "name": name or "",
                "picture": picture or "",
                "last_login": now,
            },
            "$setOnInsert": {
                "provider": "google",
                "provider_id": google_sub,
                "created_at": now,
                "resume_count": 0,
                "interviews_taken": 0,
                "average_score": 0.0,
            },
        }

        try:
            document = await self._collection.find_one_and_update(
                {"provider": "google", "provider_id": google_sub},
                update,
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            document = await self.find_by_google_sub(google_sub)
            if document is None:
                raise UserRepositoryError("Failed to upsert user") from None
            await self._collection.update_one(
                {"_id": document["_id"]},
                {
                    "$set": {
                        "email": email,
                        "name": name or "",
                        "picture": picture or "",
                        "last_login": now,
                    }
                },
            )
            document = await self._collection.find_one({"_id": document["_id"]})

        if document is None:
            raise UserRepositoryError("Failed to upsert user")

        return document

    async def find_by_id(self, user_id: str) -> dict | None:
        from bson import ObjectId
        from bson.errors import InvalidId

        try:
            oid = ObjectId(user_id)
        except InvalidId:
            return None

        return await self._collection.find_one({"_id": oid})
