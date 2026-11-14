from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

INTERVIEWS = "interview_sessions"
PREPARATION_PLANS = "preparation_plans"
RESUME_ANALYSES = "resume_analyses"

DIMENSION_FIELDS = (
    "technical_correctness",
    "relevance",
    "completeness",
    "answer_structure",
)


class InstitutionAnalyticsRepository:
    """MongoDB aggregation for institution-scoped metrics (no per-student hydration)."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._interviews = db[INTERVIEWS]
        self._plans = db[PREPARATION_PLANS]
        self._indexes_ensured = False

    async def ensure_indexes(self) -> None:
        if self._indexes_ensured:
            return
        await self._interviews.create_index(
            [("user_id", 1), ("status", 1), ("completed_at", -1)],
            name="user_status_completed",
        )
        await self._plans.create_index([("user_id", 1), ("status", 1)], name="plan_user_status")
        self._indexes_ensured = True

    def _interview_match(
        self,
        user_ids: list[str],
        date_from: datetime | None,
        date_to: datetime | None,
        job_role: str | None,
    ) -> dict:
        match: dict = {"user_id": {"$in": user_ids}, "status": "completed"}
        if date_from or date_to:
            completed: dict = {}
            if date_from:
                completed["$gte"] = date_from
            if date_to:
                completed["$lte"] = date_to
            match["completed_at"] = completed
        if job_role and job_role.strip():
            match["role"] = {"$regex": f"^{job_role.strip()}$", "$options": "i"}
        return match

    async def aggregate_interview_summary(
        self,
        user_ids: list[str],
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        job_role: str | None = None,
    ) -> dict:
        await self.ensure_indexes()
        if not user_ids:
            return {"sessions_completed": 0, "average_score": None, "active_students": 0}
        match = self._interview_match(user_ids, date_from, date_to, job_role)
        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": None,
                    "sessions_completed": {"$sum": 1},
                    "average_score": {"$avg": "$summary.average_score"},
                    "active_students": {"$addToSet": "$user_id"},
                }
            },
        ]
        rows = await self._interviews.aggregate(pipeline).to_list(length=1)
        if not rows:
            return {"sessions_completed": 0, "average_score": None, "active_students": 0}
        row = rows[0]
        return {
            "sessions_completed": int(row.get("sessions_completed", 0)),
            "average_score": row.get("average_score"),
            "active_students": len(row.get("active_students") or []),
        }

    async def aggregate_monthly_activity(
        self,
        user_ids: list[str],
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        job_role: str | None = None,
    ) -> list[dict]:
        await self.ensure_indexes()
        if not user_ids:
            return []
        match = self._interview_match(user_ids, date_from, date_to, job_role)
        pipeline = [
            {"$match": {**match, "completed_at": {"$exists": True}}},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {"format": "%Y-%m", "date": "$completed_at"},
                    },
                    "sessions": {"$sum": 1},
                    "avg_score": {"$avg": "$summary.average_score"},
                }
            },
            {"$sort": {"_id": 1}},
        ]
        rows = await self._interviews.aggregate(pipeline).to_list(length=36)
        return [
            {
                "period": row["_id"],
                "sessions": int(row.get("sessions", 0)),
                "average_score": row.get("avg_score"),
            }
            for row in rows
        ]

    async def aggregate_skill_distribution(
        self,
        user_ids: list[str],
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        job_role: str | None = None,
    ) -> dict:
        await self.ensure_indexes()
        if not user_ids:
            return {}
        match = self._interview_match(user_ids, date_from, date_to, job_role)
        group_stage = {"_id": None}
        for field in DIMENSION_FIELDS:
            group_stage[field] = {
                "$avg": f"$answers.evaluation.dimension_scores.{field}"
            }
        pipeline = [
            {"$match": match},
            {"$unwind": "$answers"},
            {
                "$match": {
                    "answers.evaluation.dimension_scores": {"$exists": True},
                }
            },
            {"$group": group_stage},
        ]
        rows = await self._interviews.aggregate(pipeline).to_list(length=1)
        if not rows:
            return {}
        row = rows[0]
        return {
            field: round(float(row.get(field) or 0), 2)
            for field in DIMENSION_FIELDS
            if row.get(field) is not None
        }

    async def aggregate_common_skill_gaps(
        self,
        user_ids: list[str],
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        job_role: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        await self.ensure_indexes()
        if not user_ids:
            return []
        match = self._interview_match(user_ids, date_from, date_to, job_role)
        pipeline = [
            {"$match": match},
            {"$unwind": "$answers"},
            {"$unwind": "$answers.evaluation.missing_concepts"},
            {
                "$group": {
                    "_id": "$answers.evaluation.missing_concepts",
                    "mention_count": {"$sum": 1},
                }
            },
            {"$sort": {"mention_count": -1}},
            {"$limit": limit},
        ]
        rows = await self._interviews.aggregate(pipeline).to_list(length=limit)
        return [
            {"concept": row["_id"], "mention_count": int(row["mention_count"])}
            for row in rows
            if row.get("_id")
        ]

    async def aggregate_preparation_plan_completion(
        self, user_ids: list[str]
    ) -> dict:
        await self.ensure_indexes()
        if not user_ids:
            return {"plans_count": 0, "average_completion_rate": None}
        pipeline = [
            {"$match": {"user_id": {"$in": user_ids}, "status": "active"}},
            {
                "$project": {
                    "days": {"$ifNull": ["$days", []]},
                }
            },
            {
                "$addFields": {
                    "all_tasks": {
                        "$reduce": {
                            "input": "$days",
                            "initialValue": [],
                            "in": {
                                "$concatArrays": [
                                    "$$value",
                                    {"$ifNull": ["$$this.tasks", []]},
                                ]
                            },
                        }
                    }
                }
            },
            {
                "$addFields": {
                    "tasks_total": {"$size": "$all_tasks"},
                    "tasks_completed": {
                        "$size": {
                            "$filter": {
                                "input": "$all_tasks",
                                "as": "t",
                                "cond": {"$eq": ["$$t.completed", True]},
                            }
                        }
                    },
                }
            },
            {
                "$group": {
                    "_id": None,
                    "plans_count": {"$sum": 1},
                    "tasks_total": {"$sum": "$tasks_total"},
                    "tasks_completed": {"$sum": "$tasks_completed"},
                }
            },
        ]
        rows = await self._plans.aggregate(pipeline).to_list(length=1)
        if not rows:
            return {"plans_count": 0, "average_completion_rate": None}
        row = rows[0]
        total = int(row.get("tasks_total") or 0)
        done = int(row.get("tasks_completed") or 0)
        rate = (done / total) if total else None
        return {
            "plans_count": int(row.get("plans_count") or 0),
            "average_completion_rate": round(rate, 3) if rate is not None else None,
        }
