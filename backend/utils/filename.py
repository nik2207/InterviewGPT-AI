import re
from pathlib import Path


def sanitize_display_filename(filename: str | None) -> str:
    """Return a safe display filename; never use as a filesystem path."""
    if not filename or not str(filename).strip():
        return "resume.pdf"

    base_name = Path(str(filename)).name
    cleaned = re.sub(r"[^\w.\- ]+", "_", base_name).strip(" .")
    if not cleaned.lower().endswith(".pdf"):
        cleaned = f"{cleaned}.pdf" if cleaned else "resume.pdf"
    return cleaned[:200]
