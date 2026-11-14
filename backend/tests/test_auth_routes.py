from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from core.dependencies import get_session_repository, get_user_repository
from core.security.jwt import create_access_token
from models.user_model import user_document_to_public
from repositories.session_repository import SessionRepository
from repositories.user_repository import UserRepository
from services.auth_service import GoogleTokenError


class InMemorySessionRepository:
    def __init__(self) -> None:
        self.revoked: set[str] = set()

    async def ensure_indexes(self) -> None:
        return None

    async def revoke_jti(self, jti: str, expires_at: datetime) -> None:
        self.revoked.add(jti)

    async def is_revoked(self, jti: str) -> bool:
        return jti in self.revoked


@pytest.fixture
def auth_client(client: TestClient, sample_user_document: dict):
    user_repo = AsyncMock(spec=UserRepository)
    user_repo.upsert_google_user = AsyncMock(return_value=sample_user_document)
    user_repo.find_by_id = AsyncMock(return_value=sample_user_document)

    session_repo = InMemorySessionRepository()

    from app.main import app

    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo

    yield client, user_repo, session_repo, sample_user_document

    app.dependency_overrides.clear()


def test_router_registered(client: TestClient):
    openapi_paths = client.app.openapi()["paths"]
    assert "/api/v1/auth/google" in openapi_paths
    assert "/api/v1/auth/me" in openapi_paths
    assert "/api/v1/auth/logout" in openapi_paths


def test_google_login_missing_token(auth_client):
    client, *_ = auth_client
    response = client.post("/api/v1/auth/google", json={})
    assert response.status_code == 422


def test_google_login_invalid_token(auth_client):
    client, *_ = auth_client
    with patch("app.api.routes.auth.verify_google_token") as mock_verify:
        mock_verify.side_effect = GoogleTokenError("Invalid Google ID token")
        response = client.post("/api/v1/auth/google", json={"token": "bad"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid Google ID token"


def test_google_login_success(auth_client, sample_google_claims):
    client, user_repo, _, sample_user_document = auth_client
    with patch("app.api.routes.auth.verify_google_token") as mock_verify:
        mock_verify.return_value = sample_google_claims
        response = client.post("/api/v1/auth/google", json={"token": "good-token"})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == sample_user_document["email"]
    user_repo.upsert_google_user.assert_awaited_once()


def test_me_requires_auth(auth_client):
    client, *_ = auth_client
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_with_valid_token(auth_client, sample_user_document):
    client, *_ = auth_client
    user_public = user_document_to_public(sample_user_document)
    token, _, _ = create_access_token(user_public.id, user_public.email)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == user_public.email


def test_me_with_malformed_token(auth_client):
    client, *_ = auth_client
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-valid"},
    )
    assert response.status_code == 401


def test_logout_revokes_session(auth_client, sample_user_document):
    client, _, session_repo, _ = auth_client
    user_public = user_document_to_public(sample_user_document)
    token, jti, _ = create_access_token(user_public.id, user_public.email)

    logout_response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == 200

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 401
    assert jti in session_repo.revoked
