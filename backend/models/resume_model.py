from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ParsingStatus = Literal["parsed", "failed"]


class ResumeInDB(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    original_filename: str
    file_size_bytes: int
    uploaded_at: datetime
    extracted_text: str
    page_count: int
    parsing_status: ParsingStatus
    content_sha256: str


class ResumeMetadata(BaseModel):
    id: str
    original_filename: str
    file_size_bytes: int
    uploaded_at: datetime
    page_count: int
    parsing_status: ParsingStatus


def resume_document_to_metadata(document: dict[str, Any]) -> ResumeMetadata:
    from bson import ObjectId

    resume_id = document.get("_id")
    if isinstance(resume_id, ObjectId):
        resume_id = str(resume_id)

    return ResumeMetadata(
        id=str(resume_id),
        original_filename=document["original_filename"],
        file_size_bytes=document["file_size_bytes"],
        uploaded_at=document["uploaded_at"],
        page_count=document["page_count"],
        parsing_status=document["parsing_status"],
    )
