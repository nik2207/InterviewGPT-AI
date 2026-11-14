import re
import secrets
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError

INSTITUTIONS = "institutions"
INSTITUTION_SUBSCRIPTION_DEFAULT = "institution_starter"
MEMBERSHIPS = "institution_memberships"
INVITATIONS = "institution_invitations"
COHORTS = "institution_cohorts"
COHORT_MEMBERS = "institution_cohort_members"
ASSIGNMENTS = "institution_assignments"
ASSIGNMENT_COMPLETIONS = "institution_assignment_completions"


class InstitutionRepositoryError(Exception):
    pass


class DuplicateMembershipError(InstitutionRepositoryError):
    pass


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "institution"
    return base[:48]


class InstitutionRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._institutions = db[INSTITUTIONS]
        self._memberships = db[MEMBERSHIPS]
        self._invitations = db[INVITATIONS]
        self._cohorts = db[COHORTS]
        self._cohort_members = db[COHORT_MEMBERS]
        self._assignments = db[ASSIGNMENTS]
        self._completions = db[ASSIGNMENT_COMPLETIONS]
        self._indexes_ensured = False

    async def ensure_indexes(self) -> None:
        if self._indexes_ensured:
            return
        await self._institutions.create_index([("slug", 1)], unique=True, name="inst_slug")
        await self._memberships.create_index(
            [("institution_id", 1), ("user_id", 1)],
            unique=True,
            name="inst_user_unique",
        )
        await self._memberships.create_index([("user_id", 1)], name="member_user")
        await self._memberships.create_index(
            [
                ("institution_id", 1),
                ("status", 1),
                ("role", 1),
                ("department", 1),
                ("course", 1),
                ("batch_label", 1),
            ],
            name="member_filters",
        )
        await self._invitations.create_index([("token", 1)], unique=True, name="invite_token")
        await self._invitations.create_index(
            [("institution_id", 1), ("email", 1), ("status", 1)],
            name="inst_invite_email",
        )
        await self._cohorts.create_index([("institution_id", 1)], name="inst_cohorts")
        await self._cohort_members.create_index(
            [("cohort_id", 1), ("user_id", 1)],
            unique=True,
            name="cohort_user",
        )
        await self._assignments.create_index([("institution_id", 1)], name="inst_assignments")
        await self._completions.create_index(
            [("assignment_id", 1), ("user_id", 1)],
            unique=True,
            name="assignment_user",
        )
        self._indexes_ensured = True

    @staticmethod
    def oid_str(value) -> str:
        if isinstance(value, ObjectId):
            return str(value)
        return str(value)

    async def create_institution(self, fields: dict) -> dict:
        await self.ensure_indexes()
        now = datetime.now(timezone.utc)
        slug = fields.get("slug") or _slugify(fields["name"])
        doc = {
            "name": fields["name"],
            "slug": slug,
            "institution_type": fields.get("institution_type", ""),
            "website": fields.get("website", ""),
            "department": fields.get("department", ""),
            "course_metadata": fields.get("course_metadata") or {},
            "status": "active",
            "subscription_plan": INSTITUTION_SUBSCRIPTION_DEFAULT,
            "seat_limit": 100,
            "created_at": now,
            "updated_at": now,
        }
        suffix = 0
        while True:
            try:
                result = await self._institutions.insert_one(doc if suffix == 0 else {**doc, "slug": f"{slug}-{suffix}"})
                doc["_id"] = result.inserted_id
                if suffix:
                    doc["slug"] = f"{slug}-{suffix}"
                return doc
            except DuplicateKeyError:
                suffix += 1
                if suffix > 50:
                    raise InstitutionRepositoryError("Unable to create institution slug") from None

    async def find_institution(self, institution_id: str) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(institution_id)
        except InvalidId:
            return None
        return await self._institutions.find_one({"_id": oid})

    async def update_institution(self, institution_id: str, fields: dict) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(institution_id)
        except InvalidId:
            return None
        fields["updated_at"] = datetime.now(timezone.utc)
        return await self._institutions.find_one_and_update(
            {"_id": oid},
            {"$set": fields},
            return_document=ReturnDocument.AFTER,
        )

    async def create_membership(self, document: dict) -> dict:
        await self.ensure_indexes()
        now = datetime.now(timezone.utc)
        document.setdefault("created_at", now)
        document.setdefault("status", "active")
        document.setdefault("consent_share_progress", False)
        try:
            result = await self._memberships.insert_one(document)
        except DuplicateKeyError:
            raise DuplicateMembershipError("User is already a member") from None
        except PyMongoError as exc:
            raise InstitutionRepositoryError("membership_insert_failed") from exc
        document["_id"] = result.inserted_id
        return document

    async def get_membership(self, institution_id: str, user_id: str) -> dict | None:
        await self.ensure_indexes()
        return await self._memberships.find_one(
            {"institution_id": institution_id, "user_id": user_id}
        )

    async def list_memberships_for_user(self, user_id: str) -> list[dict]:
        await self.ensure_indexes()
        cursor = self._memberships.find({"user_id": user_id, "status": "active"})
        return await cursor.to_list(length=200)

    async def list_members(self, institution_id: str) -> list[dict]:
        await self.ensure_indexes()
        cursor = self._memberships.find({"institution_id": institution_id}).sort(
            "created_at", -1
        )
        return await cursor.to_list(length=500)

    async def update_membership(self, membership_id: str, institution_id: str, fields: dict) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(membership_id)
        except InvalidId:
            return None
        fields["updated_at"] = datetime.now(timezone.utc)
        return await self._memberships.find_one_and_update(
            {"_id": oid, "institution_id": institution_id},
            {"$set": fields},
            return_document=ReturnDocument.AFTER,
        )

    async def create_invitation(self, institution_id: str, fields: dict) -> dict:
        await self.ensure_indexes()
        now = datetime.now(timezone.utc)
        token = secrets.token_urlsafe(32)
        doc = {
            "institution_id": institution_id,
            "email": fields["email"].lower(),
            "role": fields.get("role", "student"),
            "department": fields.get("department", ""),
            "course": fields.get("course", ""),
            "batch_label": fields.get("batch_label", ""),
            "status": "pending",
            "token": token,
            "expires_at": now + timedelta(days=14),
            "created_at": now,
        }
        result = await self._invitations.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def find_invitation_by_token(self, token: str) -> dict | None:
        await self.ensure_indexes()
        return await self._invitations.find_one({"token": token, "status": "pending"})

    async def mark_invitation_accepted(self, invitation_id: str) -> None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(invitation_id)
        except InvalidId:
            return
        await self._invitations.update_one(
            {"_id": oid},
            {"$set": {"status": "accepted", "accepted_at": datetime.now(timezone.utc)}},
        )

    async def create_cohort(self, institution_id: str, fields: dict) -> dict:
        await self.ensure_indexes()
        now = datetime.now(timezone.utc)
        doc = {
            "institution_id": institution_id,
            **fields,
            "created_at": now,
            "updated_at": now,
        }
        result = await self._cohorts.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def list_cohorts(self, institution_id: str) -> list[dict]:
        await self.ensure_indexes()
        cohorts = await self._cohorts.find({"institution_id": institution_id}).sort(
            "created_at", -1
        ).to_list(length=200)
        for cohort in cohorts:
            cid = self.oid_str(cohort["_id"])
            count = await self._cohort_members.count_documents({"cohort_id": cid})
            cohort["member_count"] = count
        return cohorts

    async def find_cohort(self, institution_id: str, cohort_id: str) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(cohort_id)
        except InvalidId:
            return None
        doc = await self._cohorts.find_one({"_id": oid, "institution_id": institution_id})
        if doc:
            doc["member_count"] = await self._cohort_members.count_documents(
                {"cohort_id": cohort_id}
            )
        return doc

    async def add_cohort_member(self, institution_id: str, cohort_id: str, user_id: str) -> bool:
        await self.ensure_indexes()
        cohort = await self.find_cohort(institution_id, cohort_id)
        if cohort is None:
            return False
        membership = await self.get_membership(institution_id, user_id)
        if membership is None or membership.get("status") != "active":
            return False
        doc = {
            "institution_id": institution_id,
            "cohort_id": cohort_id,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc),
        }
        try:
            await self._cohort_members.insert_one(doc)
            return True
        except DuplicateKeyError:
            return True

    async def list_cohort_member_user_ids(self, cohort_id: str) -> list[str]:
        await self.ensure_indexes()
        cursor = self._cohort_members.find({"cohort_id": cohort_id})
        rows = await cursor.to_list(length=2000)
        return [row["user_id"] for row in rows]

    async def list_institution_student_user_ids(self, institution_id: str) -> list[str]:
        return await self.list_filtered_student_user_ids(institution_id, {})

    async def list_filtered_student_user_ids(
        self,
        institution_id: str,
        filters: dict,
    ) -> list[str]:
        await self.ensure_indexes()
        query: dict = {
            "institution_id": institution_id,
            "status": "active",
            "role": "student",
        }
        for key in ("department", "course", "batch_label"):
            value = (filters.get(key) or "").strip()
            if value:
                query[key] = value
        rows = await self._memberships.find(query).to_list(length=10000)
        user_ids = [row["user_id"] for row in rows]
        cohort_id = (filters.get("cohort_id") or "").strip()
        if cohort_id:
            cohort_set = set(await self.list_cohort_member_user_ids(cohort_id))
            user_ids = [uid for uid in user_ids if uid in cohort_set]
        return user_ids

    async def list_members_paginated(
        self,
        institution_id: str,
        *,
        skip: int = 0,
        limit: int = 25,
        role: str | None = None,
        department: str | None = None,
    ) -> tuple[list[dict], int]:
        await self.ensure_indexes()
        query: dict = {"institution_id": institution_id, "status": {"$ne": "removed"}}
        if role:
            query["role"] = role
        if department:
            query["department"] = department
        total = await self._memberships.count_documents(query)
        cursor = (
            self._memberships.find(query)
            .sort("created_at", -1)
            .skip(max(0, skip))
            .limit(min(max(limit, 1), 100))
        )
        rows = await cursor.to_list(length=limit)
        return rows, total

    async def revoke_invitation(self, institution_id: str, invitation_id: str) -> bool:
        await self.ensure_indexes()
        try:
            oid = ObjectId(invitation_id)
        except InvalidId:
            return False
        result = await self._invitations.update_one(
            {"_id": oid, "institution_id": institution_id, "status": "pending"},
            {"$set": {"status": "revoked", "revoked_at": datetime.now(timezone.utc)}},
        )
        return result.modified_count > 0

    async def create_assignment(self, institution_id: str, document: dict) -> dict:
        await self.ensure_indexes()
        now = datetime.now(timezone.utc)
        document["institution_id"] = institution_id
        document.setdefault("created_at", now)
        result = await self._assignments.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def list_assignments(self, institution_id: str) -> list[dict]:
        await self.ensure_indexes()
        rows = await self._assignments.find({"institution_id": institution_id}).sort(
            "created_at", -1
        ).to_list(length=500)
        for row in rows:
            aid = self.oid_str(row["_id"])
            completions = await self._completions.count_documents({"assignment_id": aid})
            row["completion_count"] = completions
            cohort_id = row.get("cohort_id")
            if cohort_id:
                row["assigned_count"] = len(
                    await self.list_cohort_member_user_ids(cohort_id)
                )
            else:
                row["assigned_count"] = len(
                    await self.list_institution_student_user_ids(institution_id)
                )
        return rows

    async def find_assignment(self, institution_id: str, assignment_id: str) -> dict | None:
        await self.ensure_indexes()
        try:
            oid = ObjectId(assignment_id)
        except InvalidId:
            return None
        return await self._assignments.find_one(
            {"_id": oid, "institution_id": institution_id}
        )

    async def record_assignment_completion(
        self, institution_id: str, assignment_id: str, user_id: str, notes: str = ""
    ) -> bool:
        await self.ensure_indexes()
        assignment = await self.find_assignment(institution_id, assignment_id)
        if assignment is None:
            return False
        doc = {
            "institution_id": institution_id,
            "assignment_id": assignment_id,
            "user_id": user_id,
            "notes": notes,
            "created_at": datetime.now(timezone.utc),
        }
        try:
            await self._completions.insert_one(doc)
            return True
        except DuplicateKeyError:
            return True

    async def count_completions_for_user(self, institution_id: str, user_id: str) -> int:
        await self.ensure_indexes()
        return await self._completions.count_documents(
            {"institution_id": institution_id, "user_id": user_id}
        )

    async def count_assignments_for_institution(self, institution_id: str) -> int:
        await self.ensure_indexes()
        return await self._assignments.count_documents({"institution_id": institution_id})
