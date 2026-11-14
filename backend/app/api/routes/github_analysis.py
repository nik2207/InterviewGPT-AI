from fastapi import APIRouter, Depends, HTTPException

from core.dependencies import get_current_user, get_github_analysis_repository
from models.user_model import UserPublic
from repositories.github_analysis_repository import GitHubAnalysisRepository
from schemas.github_analysis_schema import (
    GitHubAnalysisBatchResponse,
    GitHubAnalysisDetailResponse,
    GitHubAnalysisListResponse,
    GitHubLookupRequest,
    GitHubProfileLookupResponse,
    RunGitHubAnalysisRequest,
)
from services.github_analysis_service import (
    GitHubAnalysisServiceError,
    get_github_analysis,
    list_github_analyses,
    lookup_github_profile,
    run_github_analyses,
)

router = APIRouter()


@router.post("/lookup", response_model=GitHubProfileLookupResponse)
async def github_lookup_endpoint(
    payload: GitHubLookupRequest,
    _current_user: UserPublic = Depends(get_current_user),
    repo: GitHubAnalysisRepository = Depends(get_github_analysis_repository),
) -> GitHubProfileLookupResponse:
    try:
        return await lookup_github_profile(payload, repo)
    except GitHubAnalysisServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.post("/analyses", response_model=GitHubAnalysisBatchResponse)
async def github_analyze_endpoint(
    payload: RunGitHubAnalysisRequest,
    current_user: UserPublic = Depends(get_current_user),
    repo: GitHubAnalysisRepository = Depends(get_github_analysis_repository),
) -> GitHubAnalysisBatchResponse:
    try:
        return await run_github_analyses(current_user.id, payload, repo)
    except GitHubAnalysisServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.get("/analyses", response_model=GitHubAnalysisListResponse)
async def github_list_analyses_endpoint(
    current_user: UserPublic = Depends(get_current_user),
    repo: GitHubAnalysisRepository = Depends(get_github_analysis_repository),
) -> GitHubAnalysisListResponse:
    return await list_github_analyses(current_user.id, repo)


@router.get("/analyses/{analysis_id}", response_model=GitHubAnalysisDetailResponse)
async def github_get_analysis_endpoint(
    analysis_id: str,
    current_user: UserPublic = Depends(get_current_user),
    repo: GitHubAnalysisRepository = Depends(get_github_analysis_repository),
) -> GitHubAnalysisDetailResponse:
    try:
        return await get_github_analysis(current_user.id, analysis_id, repo)
    except GitHubAnalysisServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
