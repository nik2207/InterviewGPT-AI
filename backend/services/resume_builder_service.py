from uuid import uuid4

from bson import ObjectId

from repositories.analysis_repository import AnalysisRepository
from repositories.resume_builder_repository import (
    ResumeBuilderRepository,
    ResumeBuilderRepositoryError,
)
from repositories.resume_repository import ResumeRepository
from schemas.resume_builder_schema import (
    REORDERABLE_SECTION_KEYS,
    RESUME_BUILDER_ATS_DISCLAIMER,
    CreateResumeBuilderRequest,
    ImproveBulletsRequest,
    ImproveProjectRequest,
    JobKeywordsRequest,
    PersonalInfoSection,
    ResumeAiProposalResponse,
    ResumeBuilderContent,
    ResumeBuilderDetailResponse,
    ResumeBuilderListItem,
    ResumeBuilderListResponse,
    ResumeBuilderVersion,
    SaveResumeBuilderVersionRequest,
    UpdateResumeBuilderRequest,
)
from services.gemini_resume_builder_service import (
    ResumeBuilderAiError,
    ResumeBuilderAiUnavailableError,
    payload_to_proposal,
    run_resume_builder_ai,
)
from services.resume_builder_pdf import generate_resume_builder_pdf


class ResumeBuilderServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _oid_str(value) -> str:
    if isinstance(value, ObjectId):
        return str(value)
    return str(value)


def _default_section_order() -> list[str]:
    return list(REORDERABLE_SECTION_KEYS)


def _empty_content(name: str = "", email: str = "") -> dict:
    return ResumeBuilderContent(
        personal_info=PersonalInfoSection(full_name=name, email=email),
    ).model_dump()


def _validate_section_order(order: list[str]) -> list[str]:
    allowed = set(REORDERABLE_SECTION_KEYS)
    cleaned = [key for key in order if key in allowed]
    if not cleaned:
        return _default_section_order()
    for key in REORDERABLE_SECTION_KEYS:
        if key not in cleaned:
            cleaned.append(key)
    return cleaned


def _to_detail(document: dict) -> ResumeBuilderDetailResponse:
    versions = [
        ResumeBuilderVersion.model_validate(v) for v in document.get("versions", [])
    ]
    return ResumeBuilderDetailResponse(
        id=_oid_str(document["_id"]),
        user_id=document["user_id"],
        title=document["title"],
        template=document.get("template", "classic"),
        section_order=_validate_section_order(document.get("section_order", [])),
        content=ResumeBuilderContent.model_validate(document.get("content", {})),
        versions=versions,
        source_upload_resume_id=document.get("source_upload_resume_id"),
        disclaimer=RESUME_BUILDER_ATS_DISCLAIMER,
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


async def create_resume_builder(
    user_id: str,
    payload: CreateResumeBuilderRequest,
    repo: ResumeBuilderRepository,
    resume_repo: ResumeRepository | None = None,
    analysis_repo: AnalysisRepository | None = None,
    user_name: str = "",
    user_email: str = "",
) -> ResumeBuilderDetailResponse:
    content = _empty_content(user_name, user_email)

    if payload.source_upload_resume_id and resume_repo and analysis_repo:
        upload = await resume_repo.find_by_id_for_user(
            payload.source_upload_resume_id, user_id
        )
        if upload is None:
            raise ResumeBuilderServiceError("Source resume not found.", status_code=404)
        analysis = await analysis_repo.find_latest_for_resume(
            user_id, payload.source_upload_resume_id
        )
        if analysis and analysis.get("status") == "completed":
            result = analysis.get("result") or {}
            content["professional_summary"] = (result.get("professional_summary") or "")[
                :3000
            ]
            skills = result.get("skills") or []
            content["technical_skills"] = [str(s) for s in skills[:40]]

    document = {
        "user_id": user_id,
        "title": payload.title.strip(),
        "template": payload.template,
        "section_order": _default_section_order(),
        "content": content,
        "versions": [],
        "source_upload_resume_id": payload.source_upload_resume_id,
    }

    try:
        saved = await repo.create_document(document)
    except ResumeBuilderRepositoryError:
        raise ResumeBuilderServiceError("Unable to create resume.", status_code=500) from None

    return _to_detail(saved)


async def list_resume_builders(
    user_id: str,
    repo: ResumeBuilderRepository,
) -> ResumeBuilderListResponse:
    documents = await repo.list_by_user(user_id)
    items = [
        ResumeBuilderListItem(
            id=_oid_str(doc["_id"]),
            title=doc.get("title", "Resume"),
            template=doc.get("template", "classic"),
            updated_at=doc["updated_at"],
            version_count=len(doc.get("versions", [])),
            source_upload_resume_id=doc.get("source_upload_resume_id"),
        )
        for doc in documents
    ]
    return ResumeBuilderListResponse(items=items)


async def get_resume_builder(
    user_id: str,
    doc_id: str,
    repo: ResumeBuilderRepository,
) -> ResumeBuilderDetailResponse:
    document = await repo.find_by_id_for_user(doc_id, user_id)
    if document is None:
        raise ResumeBuilderServiceError("Resume not found.", status_code=404)
    return _to_detail(document)


async def update_resume_builder(
    user_id: str,
    doc_id: str,
    payload: UpdateResumeBuilderRequest,
    repo: ResumeBuilderRepository,
) -> ResumeBuilderDetailResponse:
    document = await repo.find_by_id_for_user(doc_id, user_id)
    if document is None:
        raise ResumeBuilderServiceError("Resume not found.", status_code=404)

    update_fields: dict = {}
    if payload.title is not None:
        update_fields["title"] = payload.title.strip()
    if payload.template is not None:
        update_fields["template"] = payload.template
    if payload.section_order is not None:
        update_fields["section_order"] = _validate_section_order(payload.section_order)
    if payload.content is not None:
        update_fields["content"] = payload.content.model_dump()

    if not update_fields:
        return _to_detail(document)

    try:
        updated = await repo.update_document(doc_id, user_id, update_fields)
    except ResumeBuilderRepositoryError:
        raise ResumeBuilderServiceError("Unable to save draft.", status_code=500) from None

    if updated is None:
        raise ResumeBuilderServiceError("Resume not found.", status_code=404)
    return _to_detail(updated)


async def save_resume_builder_version(
    user_id: str,
    doc_id: str,
    payload: SaveResumeBuilderVersionRequest,
    repo: ResumeBuilderRepository,
) -> ResumeBuilderDetailResponse:
    document = await repo.find_by_id_for_user(doc_id, user_id)
    if document is None:
        raise ResumeBuilderServiceError("Resume not found.", status_code=404)

    versions = document.get("versions", [])
    version_number = len(versions) + 1
    from datetime import datetime, timezone

    version = ResumeBuilderVersion(
        version_number=version_number,
        label=payload.label.strip(),
        content=ResumeBuilderContent.model_validate(document["content"]),
        created_at=datetime.now(timezone.utc),
    )

    try:
        updated = await repo.append_version(doc_id, user_id, version.model_dump())
    except ResumeBuilderRepositoryError:
        raise ResumeBuilderServiceError("Unable to save version.", status_code=500) from None

    if updated is None:
        raise ResumeBuilderServiceError("Resume not found.", status_code=404)
    return _to_detail(updated)


async def delete_resume_builder(
    user_id: str,
    doc_id: str,
    repo: ResumeBuilderRepository,
) -> None:
    try:
        deleted = await repo.delete_document(doc_id, user_id)
    except ResumeBuilderRepositoryError:
        raise ResumeBuilderServiceError("Unable to delete resume.", status_code=500) from None
    if not deleted:
        raise ResumeBuilderServiceError("Resume not found.", status_code=404)


async def download_resume_builder_pdf(
    user_id: str,
    doc_id: str,
    repo: ResumeBuilderRepository,
) -> tuple[bytes, str]:
    document = await repo.find_by_id_for_user(doc_id, user_id)
    if document is None:
        raise ResumeBuilderServiceError("Resume not found.", status_code=404)

    content = ResumeBuilderContent.model_validate(document.get("content", {}))
    pdf = generate_resume_builder_pdf(
        title=document.get("title", "Resume"),
        template=document.get("template", "classic"),
        content=content,
        section_order=_validate_section_order(document.get("section_order", [])),
    )
    if not pdf:
        raise ResumeBuilderServiceError("PDF generation failed.", status_code=500)
    safe = _oid_str(document["_id"])[:10]
    return pdf, f"resume-{safe}.pdf"


def _content_snapshot(content: ResumeBuilderContent) -> str:
    return content.model_dump_json()


async def ai_improve_summary(
    user_id: str,
    doc_id: str,
    repo: ResumeBuilderRepository,
) -> ResumeAiProposalResponse:
    doc = await _get_doc(user_id, doc_id, repo)
    content = ResumeBuilderContent.model_validate(doc["content"])
    original = content.professional_summary.strip()
    if len(original) < 20:
        raise ResumeBuilderServiceError(
            "Add a draft professional summary before using AI improve.",
            status_code=422,
        )
    return await _run_ai("improve_summary", original, _content_snapshot(content))


async def ai_improve_bullets(
    user_id: str,
    doc_id: str,
    payload: ImproveBulletsRequest,
    repo: ResumeBuilderRepository,
) -> ResumeAiProposalResponse:
    doc = await _get_doc(user_id, doc_id, repo)
    content = ResumeBuilderContent.model_validate(doc["content"])
    entries = (
        content.work_experience
        if payload.section == "work_experience"
        else content.internships
    )
    entry = next((e for e in entries if e.id == payload.experience_id), None)
    if entry is None:
        raise ResumeBuilderServiceError("Experience entry not found.", status_code=404)
    original = "\n".join(entry.bullets).strip()
    if not original:
        raise ResumeBuilderServiceError("Add bullets before improving.", status_code=422)
    context = f"{entry.title} at {entry.company}\nBullets:\n{original}"
    return await _run_ai("improve_bullets", original, context)


async def ai_improve_project(
    user_id: str,
    doc_id: str,
    payload: ImproveProjectRequest,
    repo: ResumeBuilderRepository,
) -> ResumeAiProposalResponse:
    doc = await _get_doc(user_id, doc_id, repo)
    content = ResumeBuilderContent.model_validate(doc["content"])
    project = next((p for p in content.projects if p.id == payload.project_id), None)
    if project is None:
        raise ResumeBuilderServiceError("Project not found.", status_code=404)
    original = (project.description + "\n" + "\n".join(project.bullets)).strip()
    if len(original) < 10:
        raise ResumeBuilderServiceError("Add project content first.", status_code=422)
    return await _run_ai("improve_project", original, f"Project: {project.name}\n{original}")


async def ai_missing_info(
    user_id: str,
    doc_id: str,
    repo: ResumeBuilderRepository,
) -> ResumeAiProposalResponse:
    doc = await _get_doc(user_id, doc_id, repo)
    content = ResumeBuilderContent.model_validate(doc["content"])
    return await _run_ai("missing_info", _content_snapshot(content), "")


async def ai_job_keywords(
    user_id: str,
    doc_id: str,
    payload: JobKeywordsRequest,
    repo: ResumeBuilderRepository,
) -> ResumeAiProposalResponse:
    doc = await _get_doc(user_id, doc_id, repo)
    content = ResumeBuilderContent.model_validate(doc["content"])
    return await _run_ai(
        "job_keywords",
        _content_snapshot(content),
        f"JOB DESCRIPTION:\n{payload.job_description[:12000]}",
    )


async def ai_ats_formatting(
    user_id: str,
    doc_id: str,
    repo: ResumeBuilderRepository,
) -> ResumeAiProposalResponse:
    doc = await _get_doc(user_id, doc_id, repo)
    content = ResumeBuilderContent.model_validate(doc["content"])
    return await _run_ai("ats_formatting", _content_snapshot(content), "")


async def _get_doc(user_id: str, doc_id: str, repo: ResumeBuilderRepository) -> dict:
    document = await repo.find_by_id_for_user(doc_id, user_id)
    if document is None:
        raise ResumeBuilderServiceError("Resume not found.", status_code=404)
    return document


async def _run_ai(feature: str, original: str, context: str) -> ResumeAiProposalResponse:
    try:
        payload = run_resume_builder_ai(feature=feature, context=context)  # type: ignore[arg-type]
    except ResumeBuilderAiUnavailableError as exc:
        raise ResumeBuilderServiceError(str(exc), status_code=503) from exc
    except ResumeBuilderAiError as exc:
        raise ResumeBuilderServiceError(str(exc), status_code=422) from exc

    proposal = payload_to_proposal(feature, payload)  # type: ignore[arg-type]
    if not proposal.get("original_text"):
        proposal["original_text"] = original[:8000]
    return ResumeAiProposalResponse.model_validate(proposal)


def new_entry_id() -> str:
    return uuid4().hex[:12]
