from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.database import get_db
from core.security.jwt import TokenValidationError, decode_access_token
from models.user_model import UserPublic, user_document_to_public
from motor.motor_asyncio import AsyncIOMotorDatabase
from repositories.analysis_repository import AnalysisRepository
from repositories.interview_repository import InterviewRepository
from repositories.job_match_repository import JobMatchRepository
from repositories.career_readiness_repository import CareerReadinessRepository
from repositories.company_prep_repository import CompanyPrepRepository
from repositories.billing_repository import BillingRepository
from repositories.credit_repository import CreditRepository
from repositories.institution_analytics_repository import InstitutionAnalyticsRepository
from repositories.institution_audit_repository import InstitutionAuditRepository
from repositories.institution_repository import InstitutionRepository
from repositories.github_analysis_repository import GitHubAnalysisRepository
from repositories.job_application_repository import JobApplicationRepository
from repositories.resume_builder_repository import ResumeBuilderRepository
from repositories.preparation_plan_repository import PreparationPlanRepository
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


def get_interview_repository(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> InterviewRepository:
    return InterviewRepository(db)


def get_job_match_repository(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> JobMatchRepository:
    return JobMatchRepository(db)


def get_preparation_plan_repository(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> PreparationPlanRepository:
    return PreparationPlanRepository(db)


def get_career_readiness_repository(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CareerReadinessRepository:
    return CareerReadinessRepository(db)


def get_company_prep_repository(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CompanyPrepRepository:
    return CompanyPrepRepository(db)


def get_resume_builder_repository(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ResumeBuilderRepository:
    return ResumeBuilderRepository(db)


def get_github_analysis_repository(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> GitHubAnalysisRepository:
    return GitHubAnalysisRepository(db)


def get_job_application_repository(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> JobApplicationRepository:
    return JobApplicationRepository(db)


def get_billing_repository(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> BillingRepository:
    return BillingRepository(db)


def get_credit_repository(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CreditRepository:
    return CreditRepository(db)


def get_institution_repository(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> InstitutionRepository:
    return InstitutionRepository(db)


def get_institution_analytics_repository(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> InstitutionAnalyticsRepository:
    return InstitutionAnalyticsRepository(db)


def get_institution_audit_repository(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> InstitutionAuditRepository:
    return InstitutionAuditRepository(db)


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
