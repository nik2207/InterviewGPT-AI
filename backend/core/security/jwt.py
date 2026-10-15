from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from jose import JWTError, jwt

from core.config.settings import settings


class TokenValidationError(Exception):
    """Raised when an application JWT is invalid or expired."""


def create_access_token(user_id: str, email: str) -> tuple[str, str, datetime]:
    """Issue a signed application session JWT. Returns (token, jti, expires_at)."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    jti = str(uuid4())

    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "jti": jti,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token, jti, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    """Validate and decode an application JWT."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
            options={"require": ["sub", "exp", "jti", "iss", "aud"]},
        )
    except JWTError as exc:
        raise TokenValidationError("Invalid or expired session token") from exc

    return payload
