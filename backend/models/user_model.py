from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserInDB(BaseModel):
    """User document stored in MongoDB."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    email: EmailStr
    name: str = ""
    picture: str = ""
    provider: str = "google"
    provider_id: str
    created_at: datetime
    last_login: datetime
    resume_count: int = 0
    interviews_taken: int = 0
    average_score: float = 0.0


class UserPublic(BaseModel):
    """Safe user profile returned by the API."""

    id: str
    email: EmailStr
    name: str
    picture: str
    provider: str
    created_at: datetime
    last_login: datetime


def user_document_to_public(document: dict[str, Any]) -> UserPublic:
    from bson import ObjectId

    user_id = document.get("_id")
    if isinstance(user_id, ObjectId):
        user_id = str(user_id)

    return UserPublic(
        id=str(user_id),
        email=document["email"],
        name=document.get("name") or "",
        picture=document.get("picture") or "",
        provider=document.get("provider") or "google",
        created_at=document["created_at"],
        last_login=document["last_login"],
    )
