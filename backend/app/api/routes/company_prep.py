from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.dependencies import (
    get_analysis_repository,
    get_company_prep_repository,
    get_current_user,
    get_interview_repository,
    get_resume_repository,
)
from models.user_model import UserPublic
from repositories.analysis_repository import AnalysisRepository
from repositories.company_prep_repository import CompanyPrepRepository
from repositories.interview_repository import InterviewRepository
from repositories.resume_repository import ResumeRepository
from schemas.company_prep_schema import (
    CompanyCatalogueEntry,
    CompanyCatalogueListResponse,
    CompanyPrepDetailResponse,
    CompanyPrepListResponse,
    CreateCompanyPrepRequest,
    StartCompanyPrepInterviewRequest,
    StartCompanyPrepInterviewResponse,
    UpdateCompanyPrepChecklistRequest,
)
from services.company_prep_service import (
    CompanyPrepServiceError,
    create_company_preparation,
    get_company_detail,
    get_company_preparation,
    list_company_preparations,
    search_companies,
    start_mock_interview_from_prep,
    update_preparation_checklist,
)

router = APIRouter()


@router.get("/companies", response_model=CompanyCatalogueListResponse)
async def list_companies_endpoint(
    q: str | None = Query(default=None, max_length=80),
    _current_user: UserPublic = Depends(get_current_user),
) -> CompanyCatalogueListResponse:
    return await search_companies(q)


@router.get("/companies/{company_id}", response_model=CompanyCatalogueEntry)
async def get_company_endpoint(
    company_id: str,
    _current_user: UserPublic = Depends(get_current_user),
) -> CompanyCatalogueEntry:
    try:
        return await get_company_detail(company_id)
    except CompanyPrepServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.post(
    "/preparations",
    response_model=CompanyPrepDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prep_endpoint(
    payload: CreateCompanyPrepRequest,
    current_user: UserPublic = Depends(get_current_user),
    repo: CompanyPrepRepository = Depends(get_company_prep_repository),
) -> CompanyPrepDetailResponse:
    try:
        return await create_company_preparation(current_user.id, payload, repo)
    except CompanyPrepServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.get("/preparations", response_model=CompanyPrepListResponse)
async def list_preparations_endpoint(
    current_user: UserPublic = Depends(get_current_user),
    repo: CompanyPrepRepository = Depends(get_company_prep_repository),
) -> CompanyPrepListResponse:
    return await list_company_preparations(current_user.id, repo)


@router.get("/preparations/{prep_id}", response_model=CompanyPrepDetailResponse)
async def get_preparation_endpoint(
    prep_id: str,
    current_user: UserPublic = Depends(get_current_user),
    repo: CompanyPrepRepository = Depends(get_company_prep_repository),
) -> CompanyPrepDetailResponse:
    try:
        return await get_company_preparation(current_user.id, prep_id, repo)
    except CompanyPrepServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.patch(
    "/preparations/{prep_id}/checklist",
    response_model=CompanyPrepDetailResponse,
)
async def update_checklist_endpoint(
    prep_id: str,
    payload: UpdateCompanyPrepChecklistRequest,
    current_user: UserPublic = Depends(get_current_user),
    repo: CompanyPrepRepository = Depends(get_company_prep_repository),
) -> CompanyPrepDetailResponse:
    try:
        return await update_preparation_checklist(
            current_user.id, prep_id, payload, repo
        )
    except CompanyPrepServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.post(
    "/preparations/{prep_id}/start-interview",
    response_model=StartCompanyPrepInterviewResponse,
)
async def start_interview_endpoint(
    prep_id: str,
    payload: StartCompanyPrepInterviewRequest,
    current_user: UserPublic = Depends(get_current_user),
    prep_repo: CompanyPrepRepository = Depends(get_company_prep_repository),
    interview_repo: InterviewRepository = Depends(get_interview_repository),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repository),
) -> StartCompanyPrepInterviewResponse:
    try:
        return await start_mock_interview_from_prep(
            current_user.id,
            prep_id,
            payload,
            prep_repo,
            interview_repo,
            resume_repo,
            analysis_repo,
        )
    except CompanyPrepServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
