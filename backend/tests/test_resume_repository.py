from datetime import datetime, timezone

import pytest
from bson import ObjectId

from repositories.resume_repository import ResumeRepository


class FakeResumeCollection:
    def __init__(self) -> None:
        self.documents: dict[ObjectId, dict] = {}
        self.indexes_created = False

    async def create_index(self, *args, **kwargs):
        self.indexes_created = True

    async def insert_one(self, document: dict):
        oid = ObjectId()
        stored = document.copy()
        stored["_id"] = oid
        self.documents[oid] = stored

        class Result:
            inserted_id = oid

        return Result()

    def find(self, query: dict):
        user_id = query.get("user_id")
        matches = [
            doc for doc in self.documents.values() if doc.get("user_id") == user_id
        ]
        matches.sort(key=lambda item: item["uploaded_at"], reverse=True)

        class Cursor:
            def __init__(self, items):
                self.items = items
                self.limit_value = None

            def sort(self, field, direction):
                return self

            def limit(self, value):
                self.limit_value = value
                return self

            async def to_list(self, length):
                if self.limit_value is None:
                    return self.items[:length]
                return self.items[: self.limit_value]

        return Cursor(matches)

    async def find_one(self, query: dict):
        for doc in self.documents.values():
            if all(doc.get(key) == value for key, value in query.items()):
                return doc
        return None


class FakeResumeDatabase:
    def __init__(self) -> None:
        self.resumes = FakeResumeCollection()

    def __getitem__(self, name: str):
        if name == "resumes":
            return self.resumes
        raise KeyError(name)


@pytest.mark.asyncio
async def test_create_and_list_resumes_scoped_by_user():
    repo = ResumeRepository(FakeResumeDatabase())

    first = await repo.create_resume(
        user_id="user-a",
        original_filename="resume-a.pdf",
        file_size_bytes=1200,
        extracted_text="hidden resume text",
        page_count=1,
        content_sha256="abc",
    )
    await repo.create_resume(
        user_id="user-b",
        original_filename="resume-b.pdf",
        file_size_bytes=900,
        extracted_text="other user text",
        page_count=1,
        content_sha256="def",
    )

    user_a_resumes = await repo.list_by_user("user-a")
    assert len(user_a_resumes) == 1
    assert user_a_resumes[0]["original_filename"] == first["original_filename"]
