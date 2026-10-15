from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ParsingStatus = Literal["parsed", "failed"]


class ResumeMetadataResponse(BaseModel):
    id: str
    original_filename: str
    file_size_bytes: int
    uploaded_at: datetime
    page_count: int
    parsing_status: ParsingStatus


class ResumeUploadResponse(BaseModel):
    resume: ResumeMetadataResponse
    message: str = Field(
        default="Resume uploaded successfully. AI analysis is coming soon."
    )


class ResumeListResponse(BaseModel):
    resumes: list[ResumeMetadataResponse]
