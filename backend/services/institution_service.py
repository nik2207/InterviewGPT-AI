from datetime import datetime, timezone

from models.user_model import UserPublic
from repositories.institution_repository import (
    DuplicateMembershipError,
    InstitutionRepository,
    InstitutionRepositoryError,
)
from repositories.interview_repository import InterviewRepository
from repositories.user_repository import UserRepository
from services.institution_rbac import (
    InstitutionAccessError,
    MANAGE_ASSIGNMENTS_ROLES,
    MANAGE_COHORTS_ROLES,
    MANAGE_INSTITUTION_ROLES,
    MANAGE_MEMBERS_ROLES,
    PRIVACY_NOTE,
    VIEW_AGGREGATE_ROLES,
    assert_role,
    can_view_individual_progress,
    email_visibility_role,
    is_platform_super_admin,
)


class InstitutionServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _membership_to_dict(document: dict, repo: InstitutionRepository) -> dict:
    return {
        "id": repo.oid_str(document["_id"]),
        "institution_id": document["institution_id"],
        "user_id": document["user_id"],
        "role": document.get("role", "student"),
        "department": document.get("department", ""),
        "course": document.get("course", ""),
        "batch_label": document.get("batch_label", ""),
        "consent_share_progress": bool(document.get("consent_share_progress")),
        "status": document.get("status", "active"),
        "created_at": document.get("created_at"),
    }


def _institution_to_dict(document: dict, repo: InstitutionRepository) -> dict:
    return {
        "id": repo.oid_str(document["_id"]),
        "name": document["name"],
        "slug": document["slug"],
        "institution_type": document.get("institution_type", ""),
        "website": document.get("website", ""),
        "department": document.get("department", ""),
        "course_metadata": document.get("course_metadata") or {},
        "status": document.get("status", "active"),
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
    }


async def _require_membership(
    repo: InstitutionRepository,
    institution_id: str,
    user: UserPublic,
    allowed_roles: frozenset[str],
) -> dict:
    super_admin = is_platform_super_admin(user)
    membership = await repo.get_membership(institution_id, user.id)
    if super_admin and membership is None:
        return {
            "institution_id": institution_id,
            "user_id": user.id,
            "role": "institution_admin",
            "status": "active",
            "consent_share_progress": False,
        }
    try:
        assert_role(membership, allowed_roles)
    except InstitutionAccessError as exc:
        raise InstitutionServiceError(str(exc), status_code=exc.status_code) from exc
    return membership


async def create_institution_for_user(
    repo: InstitutionRepository,
    user: UserPublic,
    payload: dict,
) -> dict:
    try:
        institution = await repo.create_institution(payload)
    except InstitutionRepositoryError as exc:
        raise InstitutionServiceError(str(exc), status_code=500) from exc
    institution_id = repo.oid_str(institution["_id"])
    await repo.create_membership(
        {
            "institution_id": institution_id,
            "user_id": user.id,
            "role": "institution_admin",
            "department": payload.get("department", ""),
            "course": "",
            "batch_label": "",
        }
    )
    return _institution_to_dict(institution, repo)


async def list_my_memberships(
    repo: InstitutionRepository,
    user: UserPublic,
) -> list[dict]:
    memberships = await repo.list_memberships_for_user(user.id)
    items = []
    for membership in memberships:
        institution = await repo.find_institution(membership["institution_id"])
        if institution is None:
            continue
        items.append(
            {
                "institution": _institution_to_dict(institution, repo),
                "membership": _membership_to_dict(membership, repo),
            }
        )
    return items


async def get_institution_profile(
    repo: InstitutionRepository,
    institution_id: str,
    user: UserPublic,
) -> dict:
    institution = await repo.find_institution(institution_id)
    if institution is None:
        raise InstitutionServiceError("Institution not found.", status_code=404)
    super_admin = is_platform_super_admin(user)
    membership = await repo.get_membership(institution_id, user.id)
    if not super_admin and (membership is None or membership.get("status") != "active"):
        raise InstitutionServiceError("Forbidden.", status_code=403)
    return _institution_to_dict(institution, repo)


async def update_institution_profile(
    repo: InstitutionRepository,
    institution_id: str,
    user: UserPublic,
    fields: dict,
) -> dict:
    await _require_membership(repo, institution_id, user, MANAGE_INSTITUTION_ROLES)
    cleaned = {k: v for k, v in fields.items() if v is not None}
    updated = await repo.update_institution(institution_id, cleaned)
    if updated is None:
        raise InstitutionServiceError("Institution not found.", status_code=404)
    return _institution_to_dict(updated, repo)


async def invite_member(
    repo: InstitutionRepository,
    institution_id: str,
    user: UserPublic,
    payload: dict,
) -> dict:
    await _require_membership(repo, institution_id, user, MANAGE_MEMBERS_ROLES)
    if payload.get("role") == "institution_admin":
        membership = await repo.get_membership(institution_id, user.id)
        super_admin = is_platform_super_admin(user)
        if not super_admin and membership.get("role") != "institution_admin":
            raise InstitutionServiceError(
                "Only institution admins can invite other admins.",
                status_code=403,
            )
    invitation = await repo.create_invitation(institution_id, payload)
    return {
        "id": repo.oid_str(invitation["_id"]),
        "institution_id": institution_id,
        "email": invitation["email"],
        "role": invitation["role"],
        "status": invitation["status"],
        "expires_at": invitation["expires_at"],
        "invite_token": invitation["token"],
    }


async def accept_invitation(
    repo: InstitutionRepository,
    user: UserPublic,
    token: str,
) -> dict:
    invitation = await repo.find_invitation_by_token(token)
    if invitation is None:
        raise InstitutionServiceError("Invitation not found.", status_code=404)
    if invitation["expires_at"] < datetime.now(timezone.utc):
        raise InstitutionServiceError("Invitation expired.", status_code=410)
    if user.email.lower() != invitation["email"]:
        raise InstitutionServiceError(
            "This invitation was issued for a different email address.",
            status_code=403,
        )
    institution_id = invitation["institution_id"]
    existing = await repo.get_membership(institution_id, user.id)
    if existing and existing.get("status") == "active":
        await repo.mark_invitation_accepted(repo.oid_str(invitation["_id"]))
        return _membership_to_dict(existing, repo)
    try:
        membership = await repo.create_membership(
            {
                "institution_id": institution_id,
                "user_id": user.id,
                "role": invitation.get("role", "student"),
                "department": invitation.get("department", ""),
                "course": invitation.get("course", ""),
                "batch_label": invitation.get("batch_label", ""),
                "consent_share_progress": False,
            }
        )
    except DuplicateMembershipError:
        membership = await repo.get_membership(institution_id, user.id)
        if membership is None:
            raise InstitutionServiceError("Unable to join institution.", status_code=409)
    await repo.mark_invitation_accepted(repo.oid_str(invitation["_id"]))
    return _membership_to_dict(membership, repo)


async def list_institution_members(
    repo: InstitutionRepository,
    institution_id: str,
    user: UserPublic,
) -> list[dict]:
    await _require_membership(
        repo, institution_id, user, MANAGE_MEMBERS_ROLES | frozenset({"trainer"})
    )
    return [_membership_to_dict(row, repo) for row in await repo.list_members(institution_id)]


async def update_institution_member(
    repo: InstitutionRepository,
    institution_id: str,
    user: UserPublic,
    membership_id: str,
    fields: dict,
) -> dict:
    target_row = None
    for row in await repo.list_members(institution_id):
        if repo.oid_str(row["_id"]) == membership_id:
            target_row = row
            break
    if target_row is None:
        raise InstitutionServiceError("Member not found.", status_code=404)

    viewer_membership = await repo.get_membership(institution_id, user.id)
    if viewer_membership and viewer_membership.get("role") == "student":
        if target_row.get("user_id") != user.id:
            raise InstitutionServiceError("Forbidden.", status_code=403)
        allowed = {"consent_share_progress"}
        if any(k for k in fields if k not in allowed and fields[k] is not None):
            raise InstitutionServiceError(
                "Students may only update sharing consent.",
                status_code=403,
            )
        cleaned = {k: v for k, v in fields.items() if v is not None}
        updated = await repo.update_membership(membership_id, institution_id, cleaned)
        if updated is None:
            raise InstitutionServiceError("Member not found.", status_code=404)
        return _membership_to_dict(updated, repo)

    viewer = await _require_membership(repo, institution_id, user, MANAGE_MEMBERS_ROLES)
    if fields.get("role") == "institution_admin" and viewer.get("role") != "institution_admin":
        if not is_platform_super_admin(user):
            raise InstitutionServiceError("Only admins can promote to admin.", status_code=403)
    cleaned = {k: v for k, v in fields.items() if v is not None}
    updated = await repo.update_membership(membership_id, institution_id, cleaned)
    if updated is None:
        raise InstitutionServiceError("Member not found.", status_code=404)
    return _membership_to_dict(updated, repo)


async def create_cohort(
    repo: InstitutionRepository,
    institution_id: str,
    user: UserPublic,
    payload: dict,
) -> dict:
    await _require_membership(repo, institution_id, user, MANAGE_COHORTS_ROLES)
    cohort = await repo.create_cohort(institution_id, payload)
    return {
        "id": repo.oid_str(cohort["_id"]),
        "institution_id": institution_id,
        "name": cohort["name"],
        "department": cohort.get("department", ""),
        "course": cohort.get("course", ""),
        "academic_year": cohort.get("academic_year", ""),
        "description": cohort.get("description", ""),
        "member_count": 0,
        "created_at": cohort["created_at"],
    }


async def list_institution_cohorts(
    repo: InstitutionRepository,
    institution_id: str,
    user: UserPublic,
) -> list[dict]:
    await _require_membership(repo, institution_id, user, VIEW_AGGREGATE_ROLES)
    rows = await repo.list_cohorts(institution_id)
    return [
        {
            "id": repo.oid_str(row["_id"]),
            "institution_id": institution_id,
            "name": row["name"],
            "department": row.get("department", ""),
            "course": row.get("course", ""),
            "academic_year": row.get("academic_year", ""),
            "description": row.get("description", ""),
            "member_count": int(row.get("member_count", 0)),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


async def add_student_to_cohort(
    repo: InstitutionRepository,
    institution_id: str,
    cohort_id: str,
    user: UserPublic,
    student_user_id: str,
) -> bool:
    await _require_membership(repo, institution_id, user, MANAGE_COHORTS_ROLES)
    target = await repo.get_membership(institution_id, student_user_id)
    if target is None or target.get("role") != "student":
        raise InstitutionServiceError("User is not an active student member.", status_code=400)
    ok = await repo.add_cohort_member(institution_id, cohort_id, student_user_id)
    if not ok:
        raise InstitutionServiceError("Cohort not found.", status_code=404)
    return True


async def create_assignment(
    repo: InstitutionRepository,
    institution_id: str,
    user: UserPublic,
    payload: dict,
) -> dict:
    await _require_membership(repo, institution_id, user, MANAGE_ASSIGNMENTS_ROLES)
    if payload.get("cohort_id"):
        cohort = await repo.find_cohort(institution_id, payload["cohort_id"])
        if cohort is None:
            raise InstitutionServiceError("Cohort not found.", status_code=404)
    doc = {**payload, "created_by": user.id}
    assignment = await repo.create_assignment(institution_id, doc)
    return await _assignment_view(repo, assignment)


async def list_institution_assignments(
    repo: InstitutionRepository,
    institution_id: str,
    user: UserPublic,
) -> list[dict]:
    await _require_membership(
        repo,
        institution_id,
        user,
        MANAGE_ASSIGNMENTS_ROLES | frozenset({"student"}),
    )
    rows = await repo.list_assignments(institution_id)
    return [await _assignment_view(repo, row) for row in rows]


async def complete_assignment(
    repo: InstitutionRepository,
    institution_id: str,
    assignment_id: str,
    user: UserPublic,
    notes: str,
) -> dict:
    membership = await repo.get_membership(institution_id, user.id)
    if membership is None or membership.get("status") != "active":
        raise InstitutionServiceError("Forbidden.", status_code=403)
    ok = await repo.record_assignment_completion(
        institution_id, assignment_id, user.id, notes
    )
    if not ok:
        raise InstitutionServiceError("Assignment not found.", status_code=404)
    assignment = await repo.find_assignment(institution_id, assignment_id)
    return await _assignment_view(repo, assignment)


async def _assignment_view(repo: InstitutionRepository, row: dict) -> dict:
    aid = repo.oid_str(row["_id"])
    completions = row.get("completion_count")
    if completions is None:
        completions = 0
    cohort_id = row.get("cohort_id")
    assigned = row.get("assigned_count")
    if assigned is None:
        if cohort_id:
            assigned = len(await repo.list_cohort_member_user_ids(cohort_id))
        else:
            assigned = len(await repo.list_institution_student_user_ids(row["institution_id"]))
    return {
        "id": aid,
        "institution_id": row["institution_id"],
        "cohort_id": cohort_id,
        "title": row["title"],
        "activity_type": row.get("activity_type", "custom"),
        "description": row.get("description", ""),
        "due_at": row.get("due_at"),
        "job_role": row.get("job_role", ""),
        "created_by": row.get("created_by", ""),
        "created_at": row.get("created_at"),
        "completion_count": int(completions),
        "assigned_count": int(assigned),
    }


async def build_analytics_overview(
    repo: InstitutionRepository,
    interview_repo: InterviewRepository,
    institution_id: str,
    user: UserPublic,
    *,
    analytics_repo=None,
) -> dict:
    if analytics_repo is not None:
        from services.institution_analytics_service import build_analytics_dashboard

        dashboard = await build_analytics_dashboard(
            repo, analytics_repo, institution_id, user, {}
        )
        cohorts = await repo.list_cohorts(institution_id)
        assignments = await repo.list_assignments(institution_id)
        return {
            "institution_id": institution_id,
            "student_count": dashboard["total_enrolled_students"],
            "cohort_count": len(cohorts),
            "active_assignments": len(assignments),
            "assignment_completion_rate": dashboard["assignment_completion_rate"],
            "average_interview_score": dashboard["average_interview_score"],
            "readiness_trend": dashboard["monthly_activity_trend"][:6]
            or [{"label": "n/a", "avg_score": None}],
            "privacy_note": dashboard["disclaimer"],
        }

    await _require_membership(repo, institution_id, user, MANAGE_ASSIGNMENTS_ROLES)
    student_ids = await repo.list_institution_student_user_ids(institution_id)
    cohorts = await repo.list_cohorts(institution_id)
    assignments = await repo.list_assignments(institution_id)
    total_assigned = sum(int(a.get("assigned_count", 0)) for a in assignments)
    total_completed = sum(int(a.get("completion_count", 0)) for a in assignments)
    rate = (total_completed / total_assigned) if total_assigned else 0.0
    return {
        "institution_id": institution_id,
        "student_count": len(student_ids),
        "cohort_count": len(cohorts),
        "active_assignments": len(assignments),
        "assignment_completion_rate": round(rate, 3),
        "average_interview_score": None,
        "readiness_trend": [],
        "privacy_note": PRIVACY_NOTE,
    }


async def build_student_progress_snapshots(
    repo: InstitutionRepository,
    interview_repo: InterviewRepository,
    user_repo: UserRepository,
    institution_id: str,
    viewer: UserPublic,
    *,
    cohort_id: str | None = None,
) -> list[dict]:
    viewer_membership = await repo.get_membership(institution_id, viewer.id)
    super_admin = is_platform_super_admin(viewer)
    try:
        assert_role(
            viewer_membership,
            MANAGE_ASSIGNMENTS_ROLES | frozenset({"placement_officer", "student"}),
        )
    except InstitutionAccessError:
        if not super_admin:
            raise InstitutionServiceError("Forbidden.", status_code=403) from None

    if cohort_id:
        student_ids = await repo.list_cohort_member_user_ids(cohort_id)
    else:
        student_ids = await repo.list_institution_student_user_ids(institution_id)

    if viewer_membership and viewer_membership.get("role") == "student":
        student_ids = [viewer.id]

    show_email = email_visibility_role(viewer_membership, super_admin=super_admin)
    assignments = await repo.list_assignments(institution_id)
    items: list[dict] = []

    for student_id in student_ids:
        target_membership = await repo.get_membership(institution_id, student_id)
        if target_membership is None:
            continue
        individual = can_view_individual_progress(
            viewer,
            viewer_membership,
            target_membership,
            super_admin=super_admin,
        )
        if not individual and student_id != viewer.id:
            if viewer_membership and viewer_membership.get("role") == "trainer":
                continue

        user_doc = await user_repo.find_by_id(student_id)
        name = (user_doc or {}).get("name") or "Student"
        email = (user_doc or {}).get("email") if show_email and individual else None

        completed_sessions = await interview_repo.list_completed_by_user(student_id, limit=50)
        session_scores = [
            float(s.get("summary", {}).get("average_score"))
            for s in completed_sessions
            if s.get("summary", {}).get("average_score") is not None
        ]
        avg_score = sum(session_scores) / len(session_scores) if session_scores else None
        completions = await repo.count_completions_for_user(institution_id, student_id)
        assigned_total = len(assignments)

        items.append(
            {
                "user_id": student_id,
                "display_name": name,
                "email": email,
                "interviews_completed": len(completed_sessions),
                "average_interview_score": round(avg_score, 2) if avg_score is not None else None,
                "assignments_completed": completions,
                "assignments_total": assigned_total,
                "consent_share_progress": bool(
                    target_membership.get("consent_share_progress")
                ),
                "detail_level": "individual" if individual else "aggregate",
            }
        )
    return items


async def export_aggregate_csv(
    repo: InstitutionRepository,
    interview_repo: InterviewRepository,
    institution_id: str,
    user: UserPublic,
) -> str:
    await _require_membership(
        repo,
        institution_id,
        user,
        MANAGE_MEMBERS_ROLES | frozenset({"placement_officer"}),
    )
    overview = await build_analytics_overview(
        repo, interview_repo, institution_id, user
    )
    lines = [
        "metric,value",
        f"student_count,{overview['student_count']}",
        f"cohort_count,{overview['cohort_count']}",
        f"active_assignments,{overview['active_assignments']}",
        f"assignment_completion_rate,{overview['assignment_completion_rate']}",
        f"average_interview_score,{overview['average_interview_score']}",
    ]
    return "\n".join(lines) + "\n"
