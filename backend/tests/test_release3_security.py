"""Release 3 cross-tenant auth checks."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from core.dependencies import (
    get_github_analysis_repository,
    get_job_application_repository,
    get_resume_builder_repository,
    get_session_repository,
    get_user_repository,
)
from core.security.jwt import create_access_token
from tests.test_auth_routes import InMemorySessionRepository


@pytest.fixture
def r3_client(client: TestClient, sample_user_document: dict):
    from app.main import app

    builder_repo = AsyncMock()
    builder_repo.find_by_id_for_user = AsyncMock(return_value=None)

    gh_repo = AsyncMock()
    gh_repo.find_analysis_for_user = AsyncMock(return_value=None)

    app_repo = AsyncMock()
    app_repo.find_by_id_for_user = AsyncMock(return_value=None)

    user_repo = AsyncMock()
    user_repo.find_by_id = AsyncMock(return_value=sample_user_document)
    session_repo = InMemorySessionRepository()

    app.dependency_overrides[get_resume_builder_repository] = lambda: builder_repo
    app.dependency_overrides[get_github_analysis_repository] = lambda: gh_repo
    app.dependency_overrides[get_job_application_repository] = lambda: app_repo
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo

    token, _, _ = create_access_token(
        str(sample_user_document["_id"]),
        sample_user_document["email"],
    )
    headers = {"Authorization": f"Bearer {token}"}
    yield client, headers
    app.dependency_overrides.clear()


def test_resume_builder_other_user_404(r3_client):
    client, headers = r3_client
    response = client.get(
        "/api/v1/resume-builder/507f1f77bcf86cd799439050",
        headers=headers,
    )
    assert response.status_code == 404


def test_github_analysis_other_user_404(r3_client):
    client, headers = r3_client
    response = client.get(
        "/api/v1/github/analyses/507f1f77bcf86cd799439060",
        headers=headers,
    )
    assert response.status_code == 404


def test_application_other_user_404(r3_client):
    client, headers = r3_client
    response = client.get(
        "/api/v1/applications/507f1f77bcf86cd799439070",
        headers=headers,
    )
    assert response.status_code == 404


def test_github_lookup_unauthenticated(client: TestClient):
    response = client.post(
        "/api/v1/github/lookup",
        json={"input_value": "octocat"},
    )
    assert response.status_code == 401
