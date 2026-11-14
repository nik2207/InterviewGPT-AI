from collections.abc import AsyncGenerator

import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from core.config.settings import settings

_client: AsyncIOMotorClient | None = None
_database: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> None:
    """Create a single shared MongoDB client and verify connectivity."""
    global _client, _database

    _client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=20000,
    )
    _database = _client[settings.DATABASE_NAME]

    try:
        await _client.admin.command("ping")
    except Exception as exc:
        _client.close()
        _client = None
        _database = None
        raise RuntimeError(
            "Failed to connect to MongoDB. Check MONGODB_URL in backend/.env: "
            "use a valid Atlas SRV URI, URL-encode special characters in the "
            "password, and ensure Network Access allows this machine's IP."
        ) from exc


async def close_mongo_connection() -> None:
    """Close the shared MongoDB client on application shutdown."""
    global _client, _database

    if _client is not None:
        _client.close()

    _client = None
    _database = None


def get_database() -> AsyncIOMotorDatabase:
    if _database is None:
        raise RuntimeError("MongoDB is not initialized")
    return _database


async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """FastAPI dependency that yields the shared database instance."""
    yield get_database()
