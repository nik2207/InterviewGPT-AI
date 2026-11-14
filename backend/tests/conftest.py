import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Configure required settings before any application imports.
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017")
os.environ.setdefault("DATABASE_NAME", "interviewgpt_test")
os.environ.setdefault(
    "JWT_SECRET",
    "test-jwt-secret-with-sufficient-length-32chars",
)
os.environ.setdefault(
    "GOOGLE_CLIENT_ID",
    "test-client-id.apps.googleusercontent.com",
)
os.environ.setdefault("CORS_ORIGIN", "http://localhost:3000")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.0-flash")


@pytest.fixture
def client() -> TestClient:
    mock_db = MagicMock()

    async def override_get_db():
        yield mock_db

    with (
        patch("core.database.connect_to_mongo", new=AsyncMock()),
        patch("core.database.close_mongo_connection", new=AsyncMock()),
    ):
        from app.main import app
        from core.database import get_db

        app.dependency_overrides[get_db] = override_get_db

        with TestClient(app) as test_client:
            yield test_client

        app.dependency_overrides.clear()


@pytest.fixture
def sample_google_claims() -> dict:
    return {
        "iss": "https://accounts.google.com",
        "sub": "google-sub-123",
        "email": "user@example.com",
        "name": "Test User",
        "picture": "https://example.com/avatar.png",
        "aud": os.environ["GOOGLE_CLIENT_ID"],
    }


@pytest.fixture
def sample_user_document(sample_google_claims: dict) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "_id": "507f1f77bcf86cd799439011",
        "email": sample_google_claims["email"],
        "name": sample_google_claims["name"],
        "picture": sample_google_claims["picture"],
        "provider": "google",
        "provider_id": sample_google_claims["sub"],
        "created_at": now,
        "last_login": now,
        "resume_count": 0,
        "interviews_taken": 0,
        "average_score": 0.0,
    }
