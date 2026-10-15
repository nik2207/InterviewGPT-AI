from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from core.dependencies import (
    get_analysis_repository,
    get_current_user,
    get_resume_repository,
)
from models.resume_model import resume_document_to_metadata
from models.user_model import UserPublic
from repositories.resume_repository import ResumeRepository
from repositories.analysis_repository import AnalysisRepository
from schemas.analysis_schema import ResumeAnalysisResponse
from schemas.resume_schema import (
    ResumeListResponse,
    ResumeMetadataResponse,
    ResumeUploadResponse,
)
from services.resume_analysis_service import (
    ResumeAnalysisServiceError,
    analyze_resume,
    get_saved_analysis,
)
from services.resume_upload_service import process_resume_upload

router = APIRouter()


@router.post(
    "/upload",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: UserPublic = Depends(get_current_user),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
) -> ResumeUploadResponse:
    document = await process_resume_upload(
        upload=file,
        user_id=current_user.id,
        resume_repo=resume_repo,
    )
    metadata = resume_document_to_metadata(document)
    return ResumeUploadResponse(
        resume=ResumeMetadataResponse.model_validate(metadata.model_dump())
    )


@router.get("", response_model=ResumeListResponse)
async def list_resumes(
    current_user: UserPublic = Depends(get_current_user),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
) -> ResumeListResponse:
    documents = await resume_repo.list_by_user(current_user.id)
    resumes = [
        ResumeMetadataResponse.model_validate(
            resume_document_to_metadata(document).model_dump()
        )
        for document in documents
    ]
    return ResumeListResponse(resumes=resumes)


@router.post(
    "/{resume_id}/analyze",
    response_model=ResumeAnalysisResponse,
    status_code=status.HTTP_200_OK,
)
async def analyze_resume_endpoint(
    resume_id: str,
    refresh: bool = Query(default=False),
    current_user: UserPublic = Depends(get_current_user),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repository),
) -> ResumeAnalysisResponse:
    try:
        return await analyze_resume(
            user_id=current_user.id,
            resume_id=resume_id,
            resume_repo=resume_repo,
            analysis_repo=analysis_repo,
            refresh=refresh,
        )
    except ResumeAnalysisServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from None


@router.get("/{resume_id}/analysis", response_model=ResumeAnalysisResponse)
async def get_resume_analysis_endpoint(
    resume_id: str,
    current_user: UserPublic = Depends(get_current_user),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repository),
) -> ResumeAnalysisResponse:
    try:
        return await get_saved_analysis(
            user_id=current_user.id,
            resume_id=resume_id,
            resume_repo=resume_repo,
            analysis_repo=analysis_repo,
        )
    except ResumeAnalysisServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from None
