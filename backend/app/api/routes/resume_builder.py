from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from core.dependencies import (
    get_analysis_repository,
    get_current_user,
    get_resume_builder_repository,
    get_resume_repository,
)
from models.user_model import UserPublic
from repositories.analysis_repository import AnalysisRepository
from repositories.resume_builder_repository import ResumeBuilderRepository
from repositories.resume_repository import ResumeRepository
from schemas.resume_builder_schema import (
    CreateResumeBuilderRequest,
    ImproveBulletsRequest,
    ImproveProjectRequest,
    JobKeywordsRequest,
    ResumeAiProposalResponse,
    ResumeBuilderDetailResponse,
    ResumeBuilderListResponse,
    SaveResumeBuilderVersionRequest,
    UpdateResumeBuilderRequest,
)
from services.resume_builder_service import (
    ResumeBuilderServiceError,
    ai_ats_formatting,
    ai_improve_bullets,
    ai_improve_project,
    ai_improve_summary,
    ai_job_keywords,
    ai_missing_info,
    create_resume_builder,
    delete_resume_builder,
    download_resume_builder_pdf,
    get_resume_builder,
    list_resume_builders,
    save_resume_builder_version,
    update_resume_builder,
)

router = APIRouter()


@router.post(
    "",
    response_model=ResumeBuilderDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_builder_endpoint(
    payload: CreateResumeBuilderRequest,
    current_user: UserPublic = Depends(get_current_user),
    repo: ResumeBuilderRepository = Depends(get_resume_builder_repository),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repository),
) -> ResumeBuilderDetailResponse:
    try:
        return await create_resume_builder(
            current_user.id,
            payload,
            repo,
            resume_repo,
            analysis_repo,
            user_name=current_user.name,
            user_email=str(current_user.email),
        )
    except ResumeBuilderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.get("", response_model=ResumeBuilderListResponse)
async def list_builder_endpoint(
    current_user: UserPublic = Depends(get_current_user),
    repo: ResumeBuilderRepository = Depends(get_resume_builder_repository),
) -> ResumeBuilderListResponse:
    return await list_resume_builders(current_user.id, repo)


@router.get("/{doc_id}", response_model=ResumeBuilderDetailResponse)
async def get_builder_endpoint(
    doc_id: str,
    current_user: UserPublic = Depends(get_current_user),
    repo: ResumeBuilderRepository = Depends(get_resume_builder_repository),
) -> ResumeBuilderDetailResponse:
    try:
        return await get_resume_builder(current_user.id, doc_id, repo)
    except ResumeBuilderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.patch("/{doc_id}", response_model=ResumeBuilderDetailResponse)
async def update_builder_endpoint(
    doc_id: str,
    payload: UpdateResumeBuilderRequest,
    current_user: UserPublic = Depends(get_current_user),
    repo: ResumeBuilderRepository = Depends(get_resume_builder_repository),
) -> ResumeBuilderDetailResponse:
    try:
        return await update_resume_builder(current_user.id, doc_id, payload, repo)
    except ResumeBuilderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.post("/{doc_id}/versions", response_model=ResumeBuilderDetailResponse)
async def save_version_endpoint(
    doc_id: str,
    payload: SaveResumeBuilderVersionRequest,
    current_user: UserPublic = Depends(get_current_user),
    repo: ResumeBuilderRepository = Depends(get_resume_builder_repository),
) -> ResumeBuilderDetailResponse:
    try:
        return await save_resume_builder_version(current_user.id, doc_id, payload, repo)
    except ResumeBuilderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.get("/{doc_id}/pdf")
async def download_pdf_endpoint(
    doc_id: str,
    current_user: UserPublic = Depends(get_current_user),
    repo: ResumeBuilderRepository = Depends(get_resume_builder_repository),
) -> Response:
    try:
        pdf_bytes, filename = await download_resume_builder_pdf(
            current_user.id, doc_id, repo
        )
    except ResumeBuilderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_builder_endpoint(
    doc_id: str,
    current_user: UserPublic = Depends(get_current_user),
    repo: ResumeBuilderRepository = Depends(get_resume_builder_repository),
) -> None:
    try:
        await delete_resume_builder(current_user.id, doc_id, repo)
    except ResumeBuilderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.post("/{doc_id}/ai/improve-summary", response_model=ResumeAiProposalResponse)
async def ai_summary_endpoint(
    doc_id: str,
    current_user: UserPublic = Depends(get_current_user),
    repo: ResumeBuilderRepository = Depends(get_resume_builder_repository),
) -> ResumeAiProposalResponse:
    try:
        return await ai_improve_summary(current_user.id, doc_id, repo)
    except ResumeBuilderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.post("/{doc_id}/ai/improve-bullets", response_model=ResumeAiProposalResponse)
async def ai_bullets_endpoint(
    doc_id: str,
    payload: ImproveBulletsRequest,
    current_user: UserPublic = Depends(get_current_user),
    repo: ResumeBuilderRepository = Depends(get_resume_builder_repository),
) -> ResumeAiProposalResponse:
    try:
        return await ai_improve_bullets(current_user.id, doc_id, payload, repo)
    except ResumeBuilderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.post("/{doc_id}/ai/improve-project", response_model=ResumeAiProposalResponse)
async def ai_project_endpoint(
    doc_id: str,
    payload: ImproveProjectRequest,
    current_user: UserPublic = Depends(get_current_user),
    repo: ResumeBuilderRepository = Depends(get_resume_builder_repository),
) -> ResumeAiProposalResponse:
    try:
        return await ai_improve_project(current_user.id, doc_id, payload, repo)
    except ResumeBuilderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.post("/{doc_id}/ai/missing-info", response_model=ResumeAiProposalResponse)
async def ai_missing_endpoint(
    doc_id: str,
    current_user: UserPublic = Depends(get_current_user),
    repo: ResumeBuilderRepository = Depends(get_resume_builder_repository),
) -> ResumeAiProposalResponse:
    try:
        return await ai_missing_info(current_user.id, doc_id, repo)
    except ResumeBuilderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.post("/{doc_id}/ai/job-keywords", response_model=ResumeAiProposalResponse)
async def ai_keywords_endpoint(
    doc_id: str,
    payload: JobKeywordsRequest,
    current_user: UserPublic = Depends(get_current_user),
    repo: ResumeBuilderRepository = Depends(get_resume_builder_repository),
) -> ResumeAiProposalResponse:
    try:
        return await ai_job_keywords(current_user.id, doc_id, payload, repo)
    except ResumeBuilderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.post("/{doc_id}/ai/ats-formatting", response_model=ResumeAiProposalResponse)
async def ai_ats_endpoint(
    doc_id: str,
    current_user: UserPublic = Depends(get_current_user),
    repo: ResumeBuilderRepository = Depends(get_resume_builder_repository),
) -> ResumeAiProposalResponse:
    try:
        return await ai_ats_formatting(current_user.id, doc_id, repo)
    except ResumeBuilderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
