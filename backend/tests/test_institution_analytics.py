from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from core.dependencies import (
    get_institution_analytics_repository,
    get_institution_audit_repository,
    get_institution_repository,
    get_session_repository,
    get_user_repository,
)
from core.security.jwt import create_access_token
from services.institution_analytics_service import MIN_AGGREGATION_SAMPLE
from tests.fake_institution_analytics_repository import FakeInstitutionAnalyticsRepository
from tests.fake_institution_audit_repository import FakeInstitutionAuditRepository
from tests.fake_institution_repository import FakeInstitutionRepository
from tests.test_auth_routes import InMemorySessionRepository
from tests.test_institutions import _other_user_headers


@pytest.fixture
def analytics_client(client: TestClient, sample_user_document: dict):
    inst_repo = FakeInstitutionRepository()
    analytics_repo = FakeInstitutionAnalyticsRepository()
    audit_repo = FakeInstitutionAuditRepository()
    from unittest.mock import AsyncMock

    user_repo = AsyncMock()
    user_repo.find_by_id = AsyncMock(return_value=sample_user_document)
    from app.main import app

    session_repo = InMemorySessionRepository()
    app.dependency_overrides[get_institution_repository] = lambda: inst_repo
    app.dependency_overrides[get_institution_analytics_repository] = lambda: analytics_repo
    app.dependency_overrides[get_institution_audit_repository] = lambda: audit_repo
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo
    token, _, _ = create_access_token(
        str(sample_user_document["_id"]), sample_user_document["email"]
    )
    headers = {"Authorization": f"Bearer {token}"}
    yield client, inst_repo, analytics_repo, audit_repo, headers, sample_user_document
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dashboard_suppresses_small_sample():
    inst_repo = FakeInstitutionRepository()
    analytics_repo = FakeInstitutionAnalyticsRepository()
    from services.institution_analytics_service import build_analytics_dashboard
    from models.user_model import user_document_to_public

    inst = await inst_repo.create_institution({"name": "Small U"})
    iid = str(inst["_id"])
    await inst_repo.create_membership(
        {"institution_id": iid, "user_id": "admin", "role": "institution_admin"}
    )
    await inst_repo.create_membership(
        {"institution_id": iid, "user_id": "s1", "role": "student"}
    )
    user = user_document_to_public(
        {
            "_id": "admin",
            "email": "a@x.com",
            "name": "Admin",
            "created_at": datetime.now(timezone.utc),
            "last_login": datetime.now(timezone.utc),
        }
    )
    dash = await build_analytics_dashboard(inst_repo, analytics_repo, iid, user, {})
    assert dash["total_enrolled_students"] == 1
    assert dash["average_interview_score"] is None
    assert dash["skill_distribution"] == {}


@pytest.mark.asyncio
async def test_analytics_dashboard_endpoint(analytics_client):
    client, inst_repo, _analytics_repo, _audit, headers, _sample = analytics_client
    institution_id = client.post(
        "/api/v1/institutions",
        json={"name": "Analytics College"},
        headers=headers,
    ).json()["id"]
    for i in range(MIN_AGGREGATION_SAMPLE):
        await inst_repo.create_membership(
            {
                "institution_id": institution_id,
                "user_id": f"stu{i}",
                "role": "student",
                "department": "CSE",
            }
        )
    resp = client.get(
        f"/api/v1/institutions/{institution_id}/analytics/dashboard",
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_enrolled_students"] == MIN_AGGREGATION_SAMPLE
    assert body["practice_sessions_completed"] == MIN_AGGREGATION_SAMPLE * 2
    assert body["average_interview_score"] == 78.5
    assert body["not_hiring_outcome_note"]


@pytest.mark.asyncio
async def test_filter_department(analytics_client):
    client, inst_repo, _analytics, _audit, headers, _ = analytics_client
    institution_id = client.post(
        "/api/v1/institutions", json={"name": "Filter U"}, headers=headers
    ).json()["id"]
    for i in range(6):
        await inst_repo.create_membership(
            {
                "institution_id": institution_id,
                "user_id": f"u{i}",
                "role": "student",
                "department": "CSE" if i < 3 else "ECE",
            }
        )
    resp = client.get(
        f"/api/v1/institutions/{institution_id}/analytics/dashboard?department=CSE",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total_enrolled_students"] == 3


def test_paginated_admin_members(analytics_client):
    client, inst_repo, _a, _audit, headers, _ = analytics_client
    institution_id = client.post(
        "/api/v1/institutions", json={"name": "Page U"}, headers=headers
    ).json()["id"]
    resp = client.get(
        f"/api/v1/institutions/{institution_id}/admin/members?page=1&page_size=10",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_export_csv_and_pdf(analytics_client):
    client, inst_repo, _a, _audit, headers, _ = analytics_client
    institution_id = client.post(
        "/api/v1/institutions", json={"name": "Export U"}, headers=headers
    ).json()["id"]
    for i in range(6):
        await inst_repo.create_membership(
            {
                "institution_id": institution_id,
                "user_id": f"e{i}",
                "role": "student",
            }
        )
    csv_resp = client.get(
        f"/api/v1/institutions/{institution_id}/reports/export?report_type=summary&export_format=csv",
        headers=headers,
    )
    assert csv_resp.status_code == 200
    assert "not hiring" in csv_resp.text.lower() or "practice" in csv_resp.text.lower()
    pdf_resp = client.get(
        f"/api/v1/institutions/{institution_id}/reports/export?report_type=summary&export_format=pdf",
        headers=headers,
    )
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"


def test_tenant_isolation_analytics(analytics_client, sample_user_document):
    client, _inst, _a, _audit, headers, sample = analytics_client
    from unittest.mock import AsyncMock

    from core.dependencies import get_user_repository
    from app.main import app

    institution_id = client.post(
        "/api/v1/institutions", json={"name": "Secure U"}, headers=headers
    ).json()["id"]
    other_headers, other_id, other_doc = _other_user_headers(
        sample_user_document=sample
    )
    user_repo = AsyncMock()
    user_repo.find_by_id = AsyncMock(
        side_effect=lambda uid: other_doc if uid == other_id else sample
    )
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    blocked = client.get(
        f"/api/v1/institutions/{institution_id}/analytics/dashboard",
        headers=other_headers,
    )
    assert blocked.status_code == 403
