from core.config.settings import settings
from models.user_model import UserPublic

INSTITUTION_ROLES = frozenset(
    {"institution_admin", "placement_officer", "trainer", "student"}
)

ROLE_RANK = {
    "institution_admin": 100,
    "placement_officer": 80,
    "trainer": 50,
    "student": 10,
}

MANAGE_MEMBERS_ROLES = frozenset({"institution_admin", "placement_officer"})
MANAGE_COHORTS_ROLES = frozenset({"institution_admin", "placement_officer", "trainer"})
MANAGE_ASSIGNMENTS_ROLES = frozenset(
    {"institution_admin", "placement_officer", "trainer"}
)
VIEW_AGGREGATE_ROLES = frozenset(
    {"institution_admin", "placement_officer", "trainer", "student"}
)
MANAGE_INSTITUTION_ROLES = frozenset({"institution_admin"})

PRIVACY_NOTE = (
    "Individual resumes, transcripts and interview answers are never included in "
    "institution reports unless a student has explicitly enabled progress sharing."
)


class InstitutionAccessError(Exception):
    def __init__(self, message: str, status_code: int = 403) -> None:
        super().__init__(message)
        self.status_code = status_code


def is_platform_super_admin(user: UserPublic) -> bool:
    emails = getattr(settings, "PLATFORM_SUPER_ADMIN_EMAILS", "") or ""
    allowed = {e.strip().lower() for e in emails.split(",") if e.strip()}
    return user.email.lower() in allowed


def assert_role(membership: dict | None, allowed: frozenset[str]) -> None:
    if membership is None:
        raise InstitutionAccessError("Not a member of this institution.", status_code=403)
    role = membership.get("role")
    if role not in allowed:
        raise InstitutionAccessError("Insufficient institution permissions.", status_code=403)
    if membership.get("status") != "active":
        raise InstitutionAccessError("Membership is not active.", status_code=403)


def can_view_individual_progress(
    viewer: UserPublic,
    viewer_membership: dict | None,
    target_membership: dict,
    *,
    super_admin: bool = False,
) -> bool:
    if target_membership.get("user_id") == viewer.id:
        return True
    if super_admin:
        return True
    if not target_membership.get("consent_share_progress"):
        return False
    if viewer_membership is None or viewer_membership.get("status") != "active":
        return False
    role = viewer_membership.get("role")
    if role == "institution_admin":
        return True
    if role == "placement_officer":
        return True
    if role == "trainer":
        return bool(target_membership.get("consent_share_progress"))
    return False


def email_visibility_role(membership: dict | None, *, super_admin: bool) -> bool:
    if super_admin:
        return True
    if membership is None:
        return False
    return membership.get("role") in {"institution_admin", "placement_officer"}
