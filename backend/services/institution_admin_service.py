import json
from pathlib import Path

from models.user_model import UserPublic
from repositories.institution_audit_repository import InstitutionAuditRepository
from repositories.institution_repository import InstitutionRepository
from services.institution_rbac import MANAGE_INSTITUTION_ROLES, MANAGE_MEMBERS_ROLES
from services.institution_service import InstitutionServiceError, _membership_to_dict, _require_membership

_CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "institution_plan_catalog.json"


def _load_plan_catalog() -> dict:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


async def record_admin_action(
    audit_repo: InstitutionAuditRepository,
    institution_id: str,
    actor: UserPublic,
    action: str,
    detail: dict | None = None,
) -> None:
    await audit_repo.append(institution_id, actor.id, action, detail=detail)


async def list_audit_log(
    audit_repo: InstitutionAuditRepository,
    inst_repo: InstitutionRepository,
    institution_id: str,
    user: UserPublic,
    *,
    page: int = 1,
    page_size: int = 25,
) -> dict:
    await _require_membership(inst_repo, institution_id, user, MANAGE_INSTITUTION_ROLES)
    skip = (max(page, 1) - 1) * page_size
    rows, total = await audit_repo.list_for_institution(
        institution_id, skip=skip, limit=page_size
    )
    items = [
        {
            "id": audit_repo.oid_str(row.get("_id")),
            "action": row.get("action", ""),
            "actor_user_id": row.get("actor_user_id", ""),
            "detail": row.get("detail") or {},
            "created_at": row.get("created_at"),
        }
        for row in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def list_members_admin(
    inst_repo: InstitutionRepository,
    institution_id: str,
    user: UserPublic,
    *,
    page: int = 1,
    page_size: int = 25,
    role: str | None = None,
    department: str | None = None,
) -> dict:
    await _require_membership(inst_repo, institution_id, user, MANAGE_MEMBERS_ROLES)
    skip = (max(page, 1) - 1) * page_size
    rows, total = await inst_repo.list_members_paginated(
        institution_id, skip=skip, limit=page_size, role=role, department=department
    )
    return {
        "items": [_membership_to_dict(row, inst_repo) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def remove_member(
    audit_repo: InstitutionAuditRepository,
    inst_repo: InstitutionRepository,
    institution_id: str,
    user: UserPublic,
    membership_id: str,
) -> dict:
    viewer = await _require_membership(inst_repo, institution_id, user, MANAGE_MEMBERS_ROLES)
    updated = await inst_repo.update_membership(
        membership_id, institution_id, {"status": "removed"}
    )
    if updated is None:
        raise InstitutionServiceError("Member not found.", status_code=404)
    if updated.get("role") == "institution_admin" and viewer.get("role") != "institution_admin":
        raise InstitutionServiceError("Cannot remove another institution admin.", status_code=403)
    await record_admin_action(
        audit_repo,
        institution_id,
        user,
        "member_removed",
        {"membership_id": membership_id, "user_id": updated.get("user_id")},
    )
    return _membership_to_dict(updated, inst_repo)


async def get_subscription_view(
    inst_repo: InstitutionRepository,
    institution_id: str,
    user: UserPublic,
) -> dict:
    await _require_membership(inst_repo, institution_id, user, MANAGE_INSTITUTION_ROLES)
    institution = await inst_repo.find_institution(institution_id)
    if institution is None:
        raise InstitutionServiceError("Institution not found.", status_code=404)
    catalog = _load_plan_catalog()
    plan_id = institution.get("subscription_plan") or "institution_starter"
    plan = catalog.get("plans", {}).get(plan_id, {})
    seats_used = len(await inst_repo.list_institution_student_user_ids(institution_id))
    seat_limit = int(institution.get("seat_limit") or plan.get("seat_limit") or 100)
    return {
        "institution_id": institution_id,
        "subscription_plan": plan_id,
        "seat_limit": seat_limit,
        "seats_used": seats_used,
        "features": plan.get("features") or [],
        "disclaimer": catalog.get("disclaimer", ""),
    }


async def update_subscription_plan(
    audit_repo: InstitutionAuditRepository,
    inst_repo: InstitutionRepository,
    institution_id: str,
    user: UserPublic,
    plan_id: str,
) -> dict:
    await _require_membership(inst_repo, institution_id, user, MANAGE_INSTITUTION_ROLES)
    catalog = _load_plan_catalog()
    plan = catalog.get("plans", {}).get(plan_id)
    if plan is None:
        raise InstitutionServiceError("Unknown institution plan.", status_code=400)
    updated = await inst_repo.update_institution(
        institution_id,
        {
            "subscription_plan": plan_id,
            "seat_limit": int(plan.get("seat_limit", 100)),
        },
    )
    if updated is None:
        raise InstitutionServiceError("Institution not found.", status_code=404)
    await record_admin_action(
        audit_repo,
        institution_id,
        user,
        "subscription_updated",
        {"plan_id": plan_id},
    )
    return await get_subscription_view(inst_repo, institution_id, user)
