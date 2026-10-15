from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.database import get_db
from core.security.jwt import TokenValidationError, decode_access_token
from models.user_model import UserPublic, user_document_to_public
from motor.motor_asyncio import AsyncIOMotorDatabase
from repositories.analysis_repository import AnalysisRepository
from repositories.resume_repository import ResumeRepository
from repositories.session_repository import SessionRepository
from repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


def get_user_repository(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> UserRepository:
    return UserRepository(db)


def get_session_repository(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> SessionRepository:
    return SessionRepository(db)


def get_resume_repository(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ResumeRepository:
    return ResumeRepository(db)


def get_analysis_repository(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> AnalysisRepository:
    return AnalysisRepository(db)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    user_repo: UserRepository = Depends(get_user_repository),
    session_repo: SessionRepository = Depends(get_session_repository),
) -> UserPublic:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token.strip())
    except TokenValidationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    jti = payload.get("jti")
    if not jti or await session_repo.is_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    document = await user_repo.find_by_id(str(user_id))
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_document_to_public(document)


async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session_repo: SessionRepository = Depends(get_session_repository),
) -> dict:
    """Return decoded JWT payload for routes that need jti/exp (e.g. logout)."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials.strip())
    except TokenValidationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    jti = payload.get("jti")
    if not jti or await session_repo.is_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    exp = payload.get("exp")
    if exp is not None:
        payload["_expires_at"] = datetime.fromtimestamp(exp, tz=timezone.utc)

    return payload
