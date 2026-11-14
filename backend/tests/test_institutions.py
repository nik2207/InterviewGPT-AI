from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from core.dependencies import (
    get_institution_analytics_repository,
    get_institution_audit_repository,
    get_institution_repository,
    get_interview_repository,
    get_session_repository,
    get_user_repository,
)
from tests.fake_institution_analytics_repository import FakeInstitutionAnalyticsRepository
from tests.fake_institution_audit_repository import FakeInstitutionAuditRepository
from core.security.jwt import create_access_token
from repositories.institution_repository import DuplicateMembershipError
from tests.fake_institution_repository import FakeInstitutionRepository
from tests.test_auth_routes import InMemorySessionRepository


@pytest.fixture
def institution_client(client: TestClient, sample_user_document: dict):
    inst_repo = FakeInstitutionRepository()
    user_repo = AsyncMock()
    user_repo.find_by_id = AsyncMock(return_value=sample_user_document)

    interview_repo = AsyncMock()
    interview_repo.list_completed_by_user = AsyncMock(return_value=[])

    from app.main import app

    session_repo = InMemorySessionRepository()
    app.dependency_overrides[get_institution_repository] = lambda: inst_repo
    app.dependency_overrides[get_institution_analytics_repository] = (
        lambda: FakeInstitutionAnalyticsRepository()
    )
    app.dependency_overrides[get_institution_audit_repository] = (
        lambda: FakeInstitutionAuditRepository()
    )
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo
    app.dependency_overrides[get_interview_repository] = lambda: interview_repo

    token, _, _ = create_access_token(
        str(sample_user_document["_id"]), sample_user_document["email"]
    )
    headers = {"Authorization": f"Bearer {token}"}
    user_id = str(sample_user_document["_id"])
    yield client, inst_repo, headers, user_id, user_repo, interview_repo
    app.dependency_overrides.clear()


def _other_user_headers(
    email: str = "other@college.edu", sample_user_document: dict | None = None
) -> tuple[dict, str, dict]:
    other_id = str(ObjectId())
    token, _, _ = create_access_token(other_id, email)
    doc = {
        **(sample_user_document or {}),
        "_id": other_id,
        "email": email,
        "name": email.split("@")[0].title(),
    }
    return {"Authorization": f"Bearer {token}"}, other_id, doc


def test_create_institution_and_tenant_isolation(
    institution_client, sample_user_document
):
    client, _repo, headers, user_id, user_repo, _ = institution_client
    created = client.post(
        "/api/v1/institutions",
        json={"name": "ABC College of Engineering"},
        headers=headers,
    )
    assert created.status_code == 201
    institution_id = created.json()["id"]

    other_headers, other_id, other_doc = _other_user_headers(
        sample_user_document=sample_user_document
    )
    user_repo.find_by_id = AsyncMock(
        side_effect=lambda uid: other_doc if uid == other_id else sample_user_document
    )

    blocked = client.get(f"/api/v1/institutions/{institution_id}", headers=other_headers)
    assert blocked.status_code == 403

    allowed = client.get(f"/api/v1/institutions/{institution_id}", headers=headers)
    assert allowed.status_code == 200


def test_invitation_accept(institution_client, sample_user_document):
    client, _repo, headers, _admin_id, user_repo, _ = institution_client
    institution_id = client.post(
        "/api/v1/institutions",
        json={"name": "Placement Cell Institute"},
        headers=headers,
    ).json()["id"]

    student_email = "student@college.edu"
    invite = client.post(
        f"/api/v1/institutions/{institution_id}/invitations",
        json={"email": student_email, "role": "student"},
        headers=headers,
    )
    assert invite.status_code == 200
    token = invite.json()["invite_token"]

    student_headers, student_id, student_doc = _other_user_headers(
        student_email, sample_user_document
    )
    user_repo.find_by_id = AsyncMock(
        side_effect=lambda uid: student_doc if uid == student_id else sample_user_document
    )

    accept = client.post(
        "/api/v1/institutions/invitations/accept",
        json={"token": token},
        headers=student_headers,
    )
    assert accept.status_code == 200
    assert accept.json()["role"] == "student"


@pytest.mark.asyncio
async def test_duplicate_membership_rejected():
    repo = FakeInstitutionRepository()
    inst = await repo.create_institution({"name": "Dup College"})
    iid = str(inst["_id"])
    await repo.create_membership(
        {"institution_id": iid, "user_id": "user-1", "role": "student"}
    )
    with pytest.raises(DuplicateMembershipError):
        await repo.create_membership(
            {"institution_id": iid, "user_id": "user-1", "role": "student"}
        )


def test_cross_institution_attack(institution_client, sample_user_document):
    client, _repo, headers_a, _user_a, user_repo, _ = institution_client
    inst_a = client.post(
        "/api/v1/institutions",
        json={"name": "Institution Alpha"},
        headers=headers_a,
    ).json()["id"]

    headers_b, user_b, user_b_doc = _other_user_headers(
        "beta@college.edu", sample_user_document
    )
    user_repo.find_by_id = AsyncMock(
        side_effect=lambda uid: user_b_doc if uid == user_b else sample_user_document
    )
    inst_b = client.post(
        "/api/v1/institutions",
        json={"name": "Institution Beta"},
        headers=headers_b,
    ).json()["id"]

    attack = client.get(f"/api/v1/institutions/{inst_a}/members", headers=headers_b)
    assert attack.status_code == 403

    own = client.get(f"/api/v1/institutions/{inst_b}/members", headers=headers_b)
    assert own.status_code == 200


def test_student_consent_gates_trainer_progress(institution_client, sample_user_document):
    client, _repo, admin_headers, _admin_id, user_repo, _ = institution_client
    institution_id = client.post(
        "/api/v1/institutions",
        json={"name": "Consent College"},
        headers=admin_headers,
    ).json()["id"]

    student_email = "learner@college.edu"
    invite = client.post(
        f"/api/v1/institutions/{institution_id}/invitations",
        json={"email": student_email, "role": "student"},
        headers=admin_headers,
    ).json()

    student_headers, student_id, student_doc = _other_user_headers(
        student_email, sample_user_document
    )

    user_repo.find_by_id = AsyncMock(
        side_effect=lambda uid: student_doc if uid == student_id else sample_user_document
    )

    client.post(
        "/api/v1/institutions/invitations/accept",
        json={"token": invite["invite_token"]},
        headers=student_headers,
    )

    trainer_email = "trainer@college.edu"
    token_trainer = client.post(
        f"/api/v1/institutions/{institution_id}/invitations",
        json={"email": trainer_email, "role": "trainer"},
        headers=admin_headers,
    ).json()["invite_token"]
    trainer_headers, trainer_id, trainer_doc = _other_user_headers(
        trainer_email, sample_user_document
    )

    user_repo.find_by_id = AsyncMock(
        side_effect=lambda uid: (
            trainer_doc
            if uid == trainer_id
            else student_doc
            if uid == student_id
            else sample_user_document
        )
    )

    client.post(
        "/api/v1/institutions/invitations/accept",
        json={"token": token_trainer},
        headers=trainer_headers,
    )

    progress_hidden = client.get(
        f"/api/v1/institutions/{institution_id}/progress/students",
        headers=trainer_headers,
    )
    assert progress_hidden.status_code == 200
    assert progress_hidden.json() == []

    members = client.get(
        f"/api/v1/institutions/{institution_id}/members",
        headers=admin_headers,
    ).json()["items"]
    student_membership_id = next(
        item["id"] for item in members if item["user_id"] == student_id
    )

    client.patch(
        f"/api/v1/institutions/{institution_id}/members/{student_membership_id}",
        json={"consent_share_progress": True},
        headers=student_headers,
    )

    progress_visible = client.get(
        f"/api/v1/institutions/{institution_id}/progress/students",
        headers=trainer_headers,
    )
    assert progress_visible.status_code == 200
    assert len(progress_visible.json()) == 1
    assert progress_visible.json()[0]["user_id"] == student_id
    assert "email" not in progress_visible.json()[0] or progress_visible.json()[0]["email"] is None


def test_admin_export_report(institution_client):
    client, _repo, headers, *_ = institution_client
    institution_id = client.post(
        "/api/v1/institutions",
        json={"name": "Export U"},
        headers=headers,
    ).json()["id"]
    export = client.get(
        f"/api/v1/institutions/{institution_id}/reports/export"
        "?report_type=summary&export_format=csv",
        headers=headers,
    )
    assert export.status_code == 200
    assert "total_enrolled_students" in export.text
