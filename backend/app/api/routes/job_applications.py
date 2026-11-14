from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.dependencies import (
    get_analysis_repository,
    get_current_user,
    get_interview_repository,
    get_job_application_repository,
    get_job_match_repository,
    get_resume_repository,
)
from models.user_model import UserPublic
from repositories.analysis_repository import AnalysisRepository
from repositories.interview_repository import InterviewRepository
from repositories.job_application_repository import JobApplicationRepository
from repositories.job_match_repository import JobMatchRepository
from repositories.resume_repository import ResumeRepository
from schemas.job_application_schema import (
    CreateJobApplicationRequest,
    JobApplicationListResponse,
    JobApplicationResponse,
    JobApplicationStatsResponse,
    StartApplicationPracticeRequest,
    StartApplicationPracticeResponse,
    UpdateJobApplicationRequest,
)
from services.job_application_service import (
    JobApplicationServiceError,
    create_job_application,
    delete_job_application,
    get_job_application,
    job_application_stats,
    list_job_applications,
    start_application_practice,
    update_job_application,
)

router = APIRouter()


@router.post(
    "",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_application_endpoint(
    payload: CreateJobApplicationRequest,
    current_user: UserPublic = Depends(get_current_user),
    repo: JobApplicationRepository = Depends(get_job_application_repository),
) -> JobApplicationResponse:
    try:
        return await create_job_application(current_user.id, payload, repo)
    except JobApplicationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.get("/stats", response_model=JobApplicationStatsResponse)
async def application_stats_endpoint(
    current_user: UserPublic = Depends(get_current_user),
    repo: JobApplicationRepository = Depends(get_job_application_repository),
) -> JobApplicationStatsResponse:
    return await job_application_stats(current_user.id, repo)


@router.get("", response_model=JobApplicationListResponse)
async def list_applications_endpoint(
    current_user: UserPublic = Depends(get_current_user),
    repo: JobApplicationRepository = Depends(get_job_application_repository),
    status_filter: str | None = Query(default=None, alias="status", max_length=40),
    q: str | None = Query(default=None, max_length=120),
    employment_type: str | None = Query(default=None, max_length=40),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: str = Query(default="updated_at", max_length=40),
    sort_dir: int = Query(default=-1, ge=-1, le=1),
) -> JobApplicationListResponse:
    return await list_job_applications(
        current_user.id,
        repo,
        status=status_filter,
        search=q,
        employment_type=employment_type,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("/{app_id}", response_model=JobApplicationResponse)
async def get_application_endpoint(
    app_id: str,
    current_user: UserPublic = Depends(get_current_user),
    repo: JobApplicationRepository = Depends(get_job_application_repository),
) -> JobApplicationResponse:
    try:
        return await get_job_application(current_user.id, app_id, repo)
    except JobApplicationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.patch("/{app_id}", response_model=JobApplicationResponse)
async def update_application_endpoint(
    app_id: str,
    payload: UpdateJobApplicationRequest,
    current_user: UserPublic = Depends(get_current_user),
    repo: JobApplicationRepository = Depends(get_job_application_repository),
) -> JobApplicationResponse:
    try:
        return await update_job_application(current_user.id, app_id, payload, repo)
    except JobApplicationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application_endpoint(
    app_id: str,
    current_user: UserPublic = Depends(get_current_user),
    repo: JobApplicationRepository = Depends(get_job_application_repository),
) -> None:
    try:
        await delete_job_application(current_user.id, app_id, repo)
    except JobApplicationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.post(
    "/{app_id}/start-practice",
    response_model=StartApplicationPracticeResponse,
)
async def start_practice_endpoint(
    app_id: str,
    payload: StartApplicationPracticeRequest,
    current_user: UserPublic = Depends(get_current_user),
    app_repo: JobApplicationRepository = Depends(get_job_application_repository),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
    job_match_repo: JobMatchRepository = Depends(get_job_match_repository),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repository),
) -> StartApplicationPracticeResponse:
    try:
        return await start_application_practice(
            current_user.id,
            app_id,
            payload,
            app_repo,
            interview_repo,
            resume_repo,
            job_match_repo,
            analysis_repo,
        )
    except JobApplicationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
