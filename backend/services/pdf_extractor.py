from dataclasses import dataclass

import fitz

from core.config.settings import settings


class PdfExtractionError(Exception):
    """Raised when a PDF cannot be validated or parsed safely."""


@dataclass(frozen=True)
class PdfExtractionResult:
    extracted_text: str
    page_count: int


def _normalize_text(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    normalized: list[str] = []
    blank_run = 0
    for line in lines:
        if not line.strip():
            blank_run += 1
            if blank_run <= 1:
                normalized.append("")
            continue
        blank_run = 0
        normalized.append(line.strip())
    return "\n".join(normalized).strip()


def extract_text_from_pdf(content: bytes) -> PdfExtractionResult:
    if not content:
        raise PdfExtractionError("Uploaded file is empty")

    if not content.startswith(b"%PDF"):
        raise PdfExtractionError("File is not a valid PDF document")

    if len(content) > settings.RESUME_MAX_FILE_BYTES:
        raise PdfExtractionError("File exceeds the maximum allowed size")

    try:
        document = fitz.open(stream=content, filetype="pdf")
    except Exception:
        raise PdfExtractionError("Unable to parse PDF document") from None

    try:
        if document.needs_pass:
            raise PdfExtractionError(
                "Password-protected PDFs are not supported"
            )

        page_count = document.page_count
        if page_count < 1:
            raise PdfExtractionError("PDF contains no pages")

        if page_count > settings.RESUME_MAX_PAGES:
            raise PdfExtractionError(
                f"PDF exceeds the maximum of {settings.RESUME_MAX_PAGES} pages"
            )

        page_texts: list[str] = []
        for page_index in range(page_count):
            page = document.load_page(page_index)
            page_texts.append(page.get_text("text"))

        extracted = _normalize_text("\n\n".join(page_texts))

        if len(extracted) < settings.RESUME_MIN_EXTRACTED_TEXT_CHARS:
            raise PdfExtractionError(
                "This PDF does not contain enough extractable text. "
                "Scanned/image-only resumes are not supported in this phase."
            )

        if len(extracted) > settings.RESUME_MAX_EXTRACTED_TEXT_CHARS:
            raise PdfExtractionError(
                "Extracted text exceeds the maximum allowed length"
            )

        return PdfExtractionResult(
            extracted_text=extracted,
            page_count=page_count,
        )
    finally:
        document.close()
