from datetime import datetime, timedelta, timezone

from bson import ObjectId

from repositories.institution_repository import (
    DuplicateMembershipError,
    InstitutionRepository,
    _slugify,
)


class FakeInstitutionRepository(InstitutionRepository):
    """In-memory institution data for API tests."""

    def __init__(self) -> None:
        self.institutions: dict[str, dict] = {}
        self.memberships: dict[tuple[str, str], dict] = {}
        self.membership_by_id: dict[str, dict] = {}
        self.invitations: dict[str, dict] = {}
        self.cohorts: dict[str, dict] = {}
        self.cohort_members: dict[tuple[str, str], dict] = {}
        self.assignments: dict[str, dict] = {}
        self.completions: dict[tuple[str, str], dict] = {}
        self._indexes_ensured = True

    async def ensure_indexes(self) -> None:
        return None

    async def create_institution(self, fields: dict) -> dict:
        now = datetime.now(timezone.utc)
        oid = ObjectId()
        iid = str(oid)
        doc = {
            "_id": oid,
            "name": fields["name"],
            "slug": _slugify(fields["name"]),
            "institution_type": fields.get("institution_type", ""),
            "website": fields.get("website", ""),
            "department": fields.get("department", ""),
            "course_metadata": fields.get("course_metadata") or {},
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        self.institutions[iid] = doc
        return doc

    async def find_institution(self, institution_id: str) -> dict | None:
        return self.institutions.get(institution_id)

    async def update_institution(self, institution_id: str, fields: dict) -> dict | None:
        doc = self.institutions.get(institution_id)
        if doc is None:
            return None
        doc.update(fields)
        doc["updated_at"] = datetime.now(timezone.utc)
        return doc

    async def create_membership(self, document: dict) -> dict:
        key = (document["institution_id"], document["user_id"])
        if key in self.memberships:
            raise DuplicateMembershipError("exists")
        now = datetime.now(timezone.utc)
        oid = ObjectId()
        mid = str(oid)
        doc = {
            "_id": oid,
            **document,
            "created_at": now,
            "status": document.get("status", "active"),
            "consent_share_progress": bool(document.get("consent_share_progress")),
        }
        self.memberships[key] = doc
        self.membership_by_id[mid] = doc
        return doc

    async def get_membership(self, institution_id: str, user_id: str) -> dict | None:
        return self.memberships.get((institution_id, user_id))

    async def list_memberships_for_user(self, user_id: str) -> list[dict]:
        return [
            row
            for row in self.memberships.values()
            if row["user_id"] == user_id and row.get("status") == "active"
        ]

    async def list_members(self, institution_id: str) -> list[dict]:
        return [
            row for row in self.memberships.values() if row["institution_id"] == institution_id
        ]

    async def update_membership(self, membership_id: str, institution_id: str, fields: dict) -> dict | None:
        doc = self.membership_by_id.get(membership_id)
        if doc is None or doc["institution_id"] != institution_id:
            return None
        doc.update(fields)
        return doc

    async def create_invitation(self, institution_id: str, fields: dict) -> dict:
        now = datetime.now(timezone.utc)
        token = f"invite-token-{len(self.invitations)+1:02d}-abcdefghijklmnopqrst"
        oid = ObjectId()
        doc = {
            "_id": oid,
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
        self.invitations[token] = doc
        return doc

    async def find_invitation_by_token(self, token: str) -> dict | None:
        doc = self.invitations.get(token)
        if doc and doc.get("status") == "pending":
            return doc
        return None

    async def mark_invitation_accepted(self, invitation_id: str) -> None:
        for doc in self.invitations.values():
            if str(doc["_id"]) == invitation_id:
                doc["status"] = "accepted"

    async def create_cohort(self, institution_id: str, fields: dict) -> dict:
        now = datetime.now(timezone.utc)
        oid = ObjectId()
        cid = str(oid)
        doc = {"_id": oid, "institution_id": institution_id, "created_at": now, **fields}
        self.cohorts[cid] = doc
        return doc

    async def list_cohorts(self, institution_id: str) -> list[dict]:
        rows = [c for c in self.cohorts.values() if c["institution_id"] == institution_id]
        for row in rows:
            cid = str(row["_id"])
            row["member_count"] = sum(
                1 for (c_id, _u) in self.cohort_members if c_id == cid
            )
        return rows

    async def find_cohort(self, institution_id: str, cohort_id: str) -> dict | None:
        doc = self.cohorts.get(cohort_id)
        if doc is None or doc["institution_id"] != institution_id:
            return None
        doc["member_count"] = sum(
            1 for (c_id, _u) in self.cohort_members if c_id == cohort_id
        )
        return doc

    async def add_cohort_member(self, institution_id: str, cohort_id: str, user_id: str) -> bool:
        if await self.find_cohort(institution_id, cohort_id) is None:
            return False
        if await self.get_membership(institution_id, user_id) is None:
            return False
        self.cohort_members[(cohort_id, user_id)] = {
            "institution_id": institution_id,
            "cohort_id": cohort_id,
            "user_id": user_id,
        }
        return True

    async def list_cohort_member_user_ids(self, cohort_id: str) -> list[str]:
        return [uid for (cid, uid) in self.cohort_members if cid == cohort_id]

    async def list_institution_student_user_ids(self, institution_id: str) -> list[str]:
        return await self.list_filtered_student_user_ids(institution_id, {})

    async def list_filtered_student_user_ids(self, institution_id: str, filters: dict) -> list[str]:
        rows = [
            row
            for row in self.memberships.values()
            if row["institution_id"] == institution_id
            and row.get("role") == "student"
            and row.get("status") == "active"
        ]
        for key in ("department", "course", "batch_label"):
            val = (filters.get(key) or "").strip()
            if val:
                rows = [r for r in rows if r.get(key) == val]
        user_ids = [r["user_id"] for r in rows]
        cohort_id = (filters.get("cohort_id") or "").strip()
        if cohort_id:
            cohort_set = set(await self.list_cohort_member_user_ids(cohort_id))
            user_ids = [u for u in user_ids if u in cohort_set]
        return user_ids

    async def list_members_paginated(
        self, institution_id: str, *, skip=0, limit=25, role=None, department=None
    ):
        rows = [
            r
            for r in self.memberships.values()
            if r["institution_id"] == institution_id and r.get("status") != "removed"
        ]
        if role:
            rows = [r for r in rows if r.get("role") == role]
        if department:
            rows = [r for r in rows if r.get("department") == department]
        total = len(rows)
        return rows[skip : skip + limit], total

    async def create_assignment(self, institution_id: str, document: dict) -> dict:
        oid = ObjectId()
        aid = str(oid)
        doc = {"_id": oid, "institution_id": institution_id, **document}
        self.assignments[aid] = doc
        return doc

    async def list_assignments(self, institution_id: str) -> list[dict]:
        rows = [
            a for a in self.assignments.values() if a["institution_id"] == institution_id
        ]
        for row in rows:
            aid = str(row["_id"])
            row["completion_count"] = sum(
                1 for (a_id, _u) in self.completions if a_id == aid
            )
            cohort_id = row.get("cohort_id")
            if cohort_id:
                row["assigned_count"] = len(await self.list_cohort_member_user_ids(cohort_id))
            else:
                row["assigned_count"] = len(
                    await self.list_institution_student_user_ids(institution_id)
                )
        return rows

    async def find_assignment(self, institution_id: str, assignment_id: str) -> dict | None:
        doc = self.assignments.get(assignment_id)
        if doc is None or doc["institution_id"] != institution_id:
            return None
        return doc

    async def record_assignment_completion(
        self, institution_id: str, assignment_id: str, user_id: str, notes: str = ""
    ) -> bool:
        if await self.find_assignment(institution_id, assignment_id) is None:
            return False
        self.completions[(assignment_id, user_id)] = {
            "institution_id": institution_id,
            "notes": notes,
        }
        return True

    async def count_completions_for_user(self, institution_id: str, user_id: str) -> int:
        return sum(
            1
            for (_aid, uid), row in self.completions.items()
            if row["institution_id"] == institution_id and uid == user_id
        )

    async def count_assignments_for_institution(self, institution_id: str) -> int:
        return sum(
            1 for a in self.assignments.values() if a["institution_id"] == institution_id
        )
