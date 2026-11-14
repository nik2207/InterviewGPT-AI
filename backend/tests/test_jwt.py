from datetime import datetime, timedelta, timezone
import pytest
from jose import jwt

from core.config.settings import settings
from core.security.jwt import (
    TokenValidationError,
    create_access_token,
    decode_access_token,
)


def test_create_and_decode_access_token():
    token, jti, expires_at = create_access_token("user-id", "user@example.com")
    assert token
    assert jti
    assert expires_at > datetime.now(timezone.utc)

    payload = decode_access_token(token)
    assert payload["sub"] == "user-id"
    assert payload["email"] == "user@example.com"
    assert payload["jti"] == jti


def test_decode_expired_token():
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "user-id",
        "email": "user@example.com",
        "jti": "jti-expired",
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(TokenValidationError):
        decode_access_token(token)


def test_decode_token_wrong_audience():
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "user-id",
        "email": "user@example.com",
        "jti": "jti-1",
        "iss": settings.JWT_ISSUER,
        "aud": "wrong-audience",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }
    token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(TokenValidationError):
        decode_access_token(token)


def test_decode_malformed_token():
    with pytest.raises(TokenValidationError):
        decode_access_token("not.a.jwt")
