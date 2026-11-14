from fastapi import APIRouter, Depends, HTTPException, status

from core.dependencies import (
    get_current_user,
    get_current_user_payload,
    get_session_repository,
    get_user_repository,
)
from core.security.jwt import create_access_token
from models.user_model import UserPublic, user_document_to_public
from repositories.session_repository import SessionRepository
from repositories.user_repository import UserRepository, UserRepositoryError
from schemas.auth_schema import GoogleAuthRequest, GoogleAuthResponse, LogoutResponse
from services.auth_service import GoogleTokenError, verify_google_token

router = APIRouter()


@router.post("/google", response_model=GoogleAuthResponse)
async def google_login(
    payload: GoogleAuthRequest,
    user_repo: UserRepository = Depends(get_user_repository),
) -> GoogleAuthResponse:
    try:
        claims = verify_google_token(payload.token)
    except GoogleTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from None

    google_sub = str(claims["sub"])
    email = str(claims["email"])
    name = str(claims.get("name") or "")
    picture = str(claims.get("picture") or "")

    try:
        user_doc = await user_repo.upsert_google_user(
            google_sub=google_sub,
            email=email,
            name=name,
            picture=picture,
        )
    except UserRepositoryError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to complete sign-in",
        ) from None

    user_public = user_document_to_public(user_doc)
    access_token, _jti, _expires_at = create_access_token(
        user_id=user_public.id,
        email=user_public.email,
    )

    return GoogleAuthResponse(
        access_token=access_token,
        user=user_public,
    )


@router.get("/me", response_model=UserPublic)
async def get_me(
    current_user: UserPublic = Depends(get_current_user),
) -> UserPublic:
    return current_user


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    token_payload: dict = Depends(get_current_user_payload),
    session_repo: SessionRepository = Depends(get_session_repository),
) -> LogoutResponse:
    jti = token_payload.get("jti")
    expires_at = token_payload.get("_expires_at")
    if jti and expires_at is not None:
        await session_repo.revoke_jti(str(jti), expires_at)

    return LogoutResponse()
