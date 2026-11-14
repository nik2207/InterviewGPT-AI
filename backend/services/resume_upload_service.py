import hashlib

from fastapi import HTTPException, UploadFile, status

from core.config.settings import settings
from repositories.resume_repository import ResumeRepository, ResumeRepositoryError
from services.pdf_extractor import PdfExtractionError, extract_text_from_pdf
from utils.filename import sanitize_display_filename


async def read_upload_with_size_limit(upload: UploadFile) -> bytes:
    total = 0
    chunks: list[bytes] = []

    while True:
        chunk = await upload.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > settings.RESUME_MAX_FILE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File exceeds the 5 MiB upload limit",
            )
        chunks.append(chunk)

    return b"".join(chunks)


async def process_resume_upload(
    upload: UploadFile,
    user_id: str,
    resume_repo: ResumeRepository,
) -> dict:
    if upload is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A PDF file is required",
        )

    content_type = (upload.content_type or "").lower()
    if content_type and content_type not in {
        "application/pdf",
        "application/x-pdf",
    }:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported",
        )

    content = await read_upload_with_size_limit(upload)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    try:
        extraction = extract_text_from_pdf(content)
    except PdfExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from None

    checksum = hashlib.sha256(content).hexdigest()
    display_name = sanitize_display_filename(upload.filename)

    try:
        document = await resume_repo.create_resume(
            user_id=user_id,
            original_filename=display_name,
            file_size_bytes=len(content),
            extracted_text=extraction.extracted_text,
            page_count=extraction.page_count,
            content_sha256=checksum,
            parsing_status="parsed",
        )
    except ResumeRepositoryError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save resume",
        ) from None

    return document
