from datetime import datetime, timezone

import pytest
from bson import ObjectId

from repositories.user_repository import UserRepository


class FakeCollection:
    def __init__(self) -> None:
        self.documents: dict[ObjectId, dict] = {}
        self.indexes_created = False

    async def create_index(self, *args, **kwargs):
        self.indexes_created = True

    async def find_one(self, query: dict):
        if "_id" in query:
            return self.documents.get(query["_id"])
        for doc in self.documents.values():
            if all(doc.get(k) == v for k, v in query.items()):
                return doc
        return None

    async def find_one_and_update(self, query, update, upsert=False, return_document=None):
        existing = None
        for doc in self.documents.values():
            if all(doc.get(k) == v for k, v in query.items()):
                existing = doc
                break

        if existing is not None:
            if "$set" in update:
                existing.update(update["$set"])
            return existing

        if upsert:
            oid = ObjectId()
            document = {
                "_id": oid,
                **update.get("$setOnInsert", {}),
            }
            document.update(update.get("$set", {}))
            self.documents[oid] = document
            return document

        return None

    async def update_one(self, query, update):
        doc = self.documents.get(query["_id"])
        if doc:
            doc.update(update["$set"])


class FakeDatabase:
    def __init__(self) -> None:
        self.users = FakeCollection()

    def __getitem__(self, name: str):
        if name == "users":
            return self.users
        raise KeyError(name)


@pytest.mark.asyncio
async def test_upsert_google_user_creates_then_updates():
    repo = UserRepository(FakeDatabase())

    first = await repo.upsert_google_user(
        google_sub="sub-1",
        email="a@example.com",
        name="A",
        picture="p1",
    )
    assert first["provider_id"] == "sub-1"
    assert first["email"] == "a@example.com"

    second = await repo.upsert_google_user(
        google_sub="sub-1",
        email="a@example.com",
        name="A Updated",
        picture="p2",
    )
    assert second["name"] == "A Updated"
    assert second["last_login"] >= first["last_login"]
