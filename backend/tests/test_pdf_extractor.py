import pytest

from core.config.settings import settings
from services.pdf_extractor import PdfExtractionError, extract_text_from_pdf
from tests.pdf_fixtures import build_blank_pdf, build_multi_page_pdf, build_text_pdf


def test_extract_text_from_valid_pdf():
    sample_text = (
        "Jane Candidate\nSoftware Engineer with experience in Python and FastAPI."
    )
    content = build_text_pdf(sample_text)
    result = extract_text_from_pdf(content)
    assert result.page_count == 1
    assert "Jane Candidate" in result.extracted_text


def test_reject_non_pdf_bytes():
    with pytest.raises(PdfExtractionError, match="not a valid PDF"):
        extract_text_from_pdf(b"plain-text-content")


def test_reject_empty_pdf_bytes():
    with pytest.raises(PdfExtractionError, match="empty"):
        extract_text_from_pdf(b"")


def test_reject_blank_pdf_without_text():
    with pytest.raises(PdfExtractionError, match="not contain enough extractable text"):
        extract_text_from_pdf(build_blank_pdf())


def test_reject_pdf_exceeding_page_limit(monkeypatch):
    monkeypatch.setattr(settings, "RESUME_MAX_PAGES", 2)
    content = build_multi_page_pdf(
        "Valid resume content with enough extractable text for parsing.",
        pages=3,
    )
    with pytest.raises(PdfExtractionError, match="maximum"):
        extract_text_from_pdf(content)


def test_reject_pdf_exceeding_text_limit(monkeypatch):
    monkeypatch.setattr(
        "services.pdf_extractor.settings.RESUME_MIN_EXTRACTED_TEXT_CHARS",
        10,
    )
    monkeypatch.setattr(
        "services.pdf_extractor.settings.RESUME_MAX_EXTRACTED_TEXT_CHARS",
        100,
    )

    class FakePage:
        def get_text(self, _mode: str) -> str:
            return "a" * 150

    class FakeDocument:
        needs_pass = False
        page_count = 1

        def load_page(self, _index: int) -> FakePage:
            return FakePage()

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        "services.pdf_extractor.fitz.open",
        lambda **_kwargs: FakeDocument(),
    )

    with pytest.raises(PdfExtractionError, match="maximum allowed length"):
        extract_text_from_pdf(b"%PDF-1.4 mocked document bytes")
