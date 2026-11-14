from pydantic import BaseModel, Field

from models.user_model import UserPublic


class GoogleAuthRequest(BaseModel):
    token: str = Field(..., min_length=1, description="Google OAuth ID token")


class GoogleAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class LogoutResponse(BaseModel):
    message: str = "Logged out successfully"
