from datetime import datetime, timezone
from uuid import uuid4

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING, ReturnDocument
from pymongo.errors import PyMongoError

INTERVIEWS_COLLECTION = "interview_sessions"


class InterviewRepositoryError(Exception):
    pass


class InterviewRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db[INTERVIEWS_COLLECTION]
        self._indexes_ensured = False

    async def ensure_indexes(self) -> None:
        if self._indexes_ensured:
            return
        await self._collection.create_index(
            [("user_id", 1), ("created_at", DESCENDING)],
            name="user_created_at",
        )
        self._indexes_ensured = True

    async def create_session(self, document: dict) -> dict:
        await self.ensure_indexes()
        now = datetime.now(timezone.utc)
        document.setdefault("created_at", now)
        document.setdefault("updated_at", now)
        try:
            result = await self._collection.insert_one(document)
        except PyMongoError:
            raise InterviewRepositoryError("Failed to create interview session") from None
        document["_id"] = result.inserted_id
        return document

    async def find_by_id_for_user(self, session_id: str, user_id: str) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(session_id)
        except InvalidId:
            return None
        return await self._collection.find_one({"_id": oid, "user_id": user_id})

    async def list_completed_by_user(self, user_id: str, limit: int = 50) -> list[dict]:
        await self.ensure_indexes()
        cursor = (
            self._collection.find({"user_id": user_id, "status": "completed"})
            .sort("completed_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def list_by_user(self, user_id: str, limit: int = 30) -> list[dict]:
        await self.ensure_indexes()
        cursor = (
            self._collection.find({"user_id": user_id})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def append_answer_pending(
        self,
        session_id: str,
        user_id: str,
        question_index: int,
        answer_record: dict,
    ) -> dict | None:
        """Atomically append a pending answer if question index matches and slot is free."""
        await self.ensure_indexes()
        try:
            oid = ObjectId(session_id)
        except InvalidId:
            return None

        now = datetime.now(timezone.utc)
        filter_query = {
            "_id": oid,
            "user_id": user_id,
            "status": "in_progress",
            "current_question_index": question_index,
            "answers.question_id": {"$ne": answer_record["question_id"]},
        }
        update = {
            "$push": {"answers": answer_record},
            "$set": {"updated_at": now},
        }
        try:
            return await self._collection.find_one_and_update(
                filter_query,
                update,
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError:
            raise InterviewRepositoryError("Failed to save answer") from None

    async def update_answer_evaluation(
        self,
        session_id: str,
        user_id: str,
        question_id: str,
        submission_id: str,
        evaluation_status: str,
        evaluation: dict | None,
        evaluation_error: str | None,
        advance_index: bool,
    ) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(session_id)
        except InvalidId:
            return None

        now = datetime.now(timezone.utc)
        session = await self._collection.find_one(
            {"_id": oid, "user_id": user_id, "status": "in_progress"}
        )
        if session is None:
            return None

        answers = session.get("answers", [])
        updated_answers = []
        found = False
        for item in answers:
            if (
                item.get("question_id") == question_id
                and item.get("submission_id") == submission_id
            ):
                found = True
                item = {
                    **item,
                    "evaluation_status": evaluation_status,
                    "evaluation": evaluation,
                    "evaluation_error": evaluation_error,
                    "evaluated_at": now if evaluation_status == "evaluated" else None,
                }
            updated_answers.append(item)

        if not found:
            return None

        update_fields: dict = {
            "answers": updated_answers,
            "updated_at": now,
        }
        if advance_index and evaluation_status == "evaluated":
            update_fields["current_question_index"] = int(
                session.get("current_question_index", 0)
            ) + 1

        try:
            return await self._collection.find_one_and_update(
                {"_id": oid, "user_id": user_id, "status": "in_progress"},
                {"$set": update_fields},
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError:
            raise InterviewRepositoryError("Failed to update evaluation") from None

    def find_answer_by_submission(
        self, session: dict, question_id: str, submission_id: str
    ) -> dict | None:
        for item in session.get("answers", []):
            if (
                item.get("question_id") == question_id
                and item.get("submission_id") == submission_id
            ):
                return item
        return None

    def find_answer_for_question(self, session: dict, question_id: str) -> dict | None:
        for item in reversed(session.get("answers", [])):
            if item.get("question_id") == question_id:
                return item
        return None

    async def delete_session_for_user(self, session_id: str, user_id: str) -> bool:
        await self.ensure_indexes()
        try:
            oid = ObjectId(session_id)
        except InvalidId:
            return False
        try:
            result = await self._collection.delete_one(
                {"_id": oid, "user_id": user_id}
            )
        except PyMongoError:
            raise InterviewRepositoryError("Failed to delete interview session") from None
        return result.deleted_count == 1

    async def set_review_bookmarks(
        self,
        session_id: str,
        user_id: str,
        question_ids: list[str],
    ) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(session_id)
        except InvalidId:
            return None

        session = await self._collection.find_one({"_id": oid, "user_id": user_id})
        if session is None:
            return None

        valid_ids = {q.get("id") for q in session.get("questions", [])}
        cleaned = [qid for qid in question_ids if qid in valid_ids][:30]
        now = datetime.now(timezone.utc)
        try:
            return await self._collection.find_one_and_update(
                {"_id": oid, "user_id": user_id},
                {"$set": {"review_bookmarks": cleaned, "updated_at": now}},
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError:
            raise InterviewRepositoryError("Failed to update bookmarks") from None

    async def upsert_practice_revision(
        self,
        session_id: str,
        user_id: str,
        question_id: str,
        draft_text: str,
    ) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(session_id)
        except InvalidId:
            return None

        session = await self._collection.find_one({"_id": oid, "user_id": user_id})
        if session is None:
            return None

        if not any(q.get("id") == question_id for q in session.get("questions", [])):
            return None

        now = datetime.now(timezone.utc)
        revisions = list(session.get("practice_revisions") or [])
        updated = False
        for item in revisions:
            if item.get("question_id") == question_id:
                item["draft_text"] = draft_text
                item["updated_at"] = now
                updated = True
                break
        if not updated:
            revisions.append(
                {
                    "question_id": question_id,
                    "draft_text": draft_text,
                    "updated_at": now,
                }
            )

        try:
            return await self._collection.find_one_and_update(
                {"_id": oid, "user_id": user_id},
                {"$set": {"practice_revisions": revisions, "updated_at": now}},
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError:
            raise InterviewRepositoryError("Failed to save practice revision") from None

    async def complete_session(
        self,
        session_id: str,
        user_id: str,
        summary: dict,
    ) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(session_id)
        except InvalidId:
            return None

        now = datetime.now(timezone.utc)
        try:
            return await self._collection.find_one_and_update(
                {
                    "_id": oid,
                    "user_id": user_id,
                    "status": "in_progress",
                },
                {
                    "$set": {
                        "status": "completed",
                        "summary": summary,
                        "completed_at": now,
                        "updated_at": now,
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError:
            raise InterviewRepositoryError("Failed to complete session") from None

    @staticmethod
    def new_submission_id() -> str:
        return uuid4().hex

    async def insert_follow_up_question(
        self,
        session_id: str,
        user_id: str,
        current_index: int,
        question: dict,
        parent_question_id: str,
    ) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(session_id)
        except InvalidId:
            return None

        session = await self._collection.find_one(
            {
                "_id": oid,
                "user_id": user_id,
                "status": "in_progress",
                "current_question_index": current_index,
            }
        )
        if session is None:
            return None

        questions = list(session.get("questions", []))
        if any(
            q.get("parent_question_id") == parent_question_id and q.get("is_follow_up")
            for q in questions
        ):
            return None

        insert_at = current_index + 1
        if insert_at > len(questions):
            insert_at = len(questions)
        questions.insert(insert_at, question)

        now = datetime.now(timezone.utc)
        try:
            return await self._collection.find_one_and_update(
                {
                    "_id": oid,
                    "user_id": user_id,
                    "status": "in_progress",
                },
                {
                    "$set": {
                        "questions": questions,
                        "current_question_index": insert_at,
                        "updated_at": now,
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError:
            raise InterviewRepositoryError("Failed to insert follow-up") from None

    async def advance_question_index(
        self,
        session_id: str,
        user_id: str,
        expected_index: int,
    ) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(session_id)
        except InvalidId:
            return None

        now = datetime.now(timezone.utc)
        try:
            return await self._collection.find_one_and_update(
                {
                    "_id": oid,
                    "user_id": user_id,
                    "status": "in_progress",
                    "current_question_index": expected_index,
                },
                {
                    "$set": {
                        "current_question_index": expected_index + 1,
                        "updated_at": now,
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError:
            raise InterviewRepositoryError("Failed to advance index") from None

    async def skip_follow_up_question(
        self,
        session_id: str,
        user_id: str,
        question_id: str,
    ) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(session_id)
        except InvalidId:
            return None

        session = await self._collection.find_one(
            {"_id": oid, "user_id": user_id, "status": "in_progress"}
        )
        if session is None:
            return None

        questions = list(session.get("questions", []))
        index = int(session.get("current_question_index", 0))
        if index >= len(questions) or questions[index].get("id") != question_id:
            return None

        questions[index] = {**questions[index], "skipped": True}
        now = datetime.now(timezone.utc)
        try:
            return await self._collection.find_one_and_update(
                {"_id": oid, "user_id": user_id, "status": "in_progress"},
                {
                    "$set": {
                        "questions": questions,
                        "current_question_index": index + 1,
                        "updated_at": now,
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError:
            raise InterviewRepositoryError("Failed to skip follow-up") from None

    async def append_voice_transcript(
        self,
        session_id: str,
        user_id: str,
        entry: dict,
    ) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(session_id)
        except InvalidId:
            return None

        now = datetime.now(timezone.utc)
        entry.setdefault("created_at", now)
        try:
            return await self._collection.find_one_and_update(
                {
                    "_id": oid,
                    "user_id": user_id,
                    "status": "in_progress",
                    "voice_interview.enabled": True,
                },
                {
                    "$push": {"voice_interview.transcript": entry},
                    "$set": {"updated_at": now},
                },
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError:
            raise InterviewRepositoryError("Failed to append transcript") from None

    async def update_voice_session_status(
        self,
        session_id: str,
        user_id: str,
        session_status: str,
    ) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(session_id)
        except InvalidId:
            return None

        now = datetime.now(timezone.utc)
        try:
            return await self._collection.find_one_and_update(
                {
                    "_id": oid,
                    "user_id": user_id,
                    "status": "in_progress",
                    "voice_interview.enabled": True,
                },
                {
                    "$set": {
                        "voice_interview.session_status": session_status,
                        "updated_at": now,
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError:
            raise InterviewRepositoryError("Failed to update voice status") from None
