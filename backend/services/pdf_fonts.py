"""Register system Unicode fonts for PDF content when available."""

import os
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_REGISTERED: list[str] = []
_FONT_CANDIDATES = (
    os.getenv("PDF_UNICODE_FONT_PATH", ""),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    r"C:\Windows\Fonts\ARIALUNI.TTF",
    r"C:\Windows\Fonts\mangal.ttf",
    r"C:\Windows\Fonts\arial.ttf",
)


def _fonts() -> list[str]:
    if _REGISTERED:
        return _REGISTERED
    for index, candidate in enumerate(_FONT_CANDIDATES):
        if not candidate:
            continue
        path = Path(candidate)
        if not path.is_file():
            continue
        name = f"SmartUnicode{index}"
        try:
            pdfmetrics.registerFont(TTFont(name, str(path)))
        except Exception:
            continue
        _REGISTERED.append(name)
    return _REGISTERED


def pdf_font_for(text: str, *, bold: bool = False) -> str:
    """Pick an installed TTF that contains every character in this text line."""
    fonts = _fonts()
    for name in fonts:
        face = pdfmetrics.getFont(name).face
        if all(ord(char) in face.charWidths or char.isspace() for char in text):
            return name
    return "Helvetica-Bold" if bold else "Helvetica"
