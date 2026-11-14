from datetime import datetime


class FakeInstitutionAnalyticsRepository:
    def __init__(self) -> None:
        self.sessions_per_user = 2
        self.avg_score = 78.5
        self._indexes_ensured = True

    async def ensure_indexes(self) -> None:
        return None

    async def aggregate_interview_summary(
        self,
        user_ids: list[str],
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        job_role: str | None = None,
    ) -> dict:
        if not user_ids:
            return {"sessions_completed": 0, "average_score": None, "active_students": 0}
        sessions = len(user_ids) * self.sessions_per_user
        return {
            "sessions_completed": sessions,
            "average_score": self.avg_score,
            "active_students": len(user_ids),
        }

    async def aggregate_monthly_activity(self, user_ids, **kwargs) -> list[dict]:
        if not user_ids:
            return []
        return [
            {"period": "2025-10", "sessions": len(user_ids), "average_score": self.avg_score},
            {"period": "2025-11", "sessions": len(user_ids) * 2, "average_score": self.avg_score},
        ]

    async def aggregate_skill_distribution(self, user_ids, **kwargs) -> dict:
        if len(user_ids) < 5:
            return {}
        return {
            "technical_correctness": 3.8,
            "relevance": 4.0,
            "completeness": 3.5,
            "answer_structure": 3.7,
        }

    async def aggregate_common_skill_gaps(
        self, user_ids, *, limit: int = 10, **kwargs
    ) -> list[dict]:
        if len(user_ids) < 5:
            return []
        return [{"concept": "System design depth", "mention_count": 12}]

    async def aggregate_preparation_plan_completion(self, user_ids: list[str]) -> dict:
        if not user_ids:
            return {"plans_count": 0, "average_completion_rate": None}
        return {"plans_count": len(user_ids), "average_completion_rate": 0.42}
