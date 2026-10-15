from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    MONGODB_URL: str
    DATABASE_NAME: str = "interviewgpt"
    CORS_ORIGIN: str = "http://localhost:3000"

    GOOGLE_CLIENT_ID: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "interviewgpt-api"
    JWT_AUDIENCE: str = "interviewgpt-client"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    RESUME_MAX_FILE_BYTES: int = 5 * 1024 * 1024
    RESUME_MAX_PAGES: int = 50
    RESUME_MAX_EXTRACTED_TEXT_CHARS: int = 400_000
    RESUME_MIN_EXTRACTED_TEXT_CHARS: int = 40

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_REQUEST_TIMEOUT_SECONDS: int = 120

    @field_validator("MONGODB_URL")
    @classmethod
    def mongodb_url_must_be_set(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError(
                "MONGODB_URL must be set in backend/.env "
                "(MongoDB Atlas connection string)"
            )
        return value.strip()

    @field_validator("DATABASE_NAME")
    @classmethod
    def database_name_must_be_set(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("DATABASE_NAME must be set in backend/.env")
        return value.strip()

    @field_validator("GOOGLE_CLIENT_ID")
    @classmethod
    def google_client_id_must_be_set(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned or cleaned == "your_google_client_id":
            raise ValueError(
                "GOOGLE_CLIENT_ID must be set in backend/.env "
                "(Google OAuth Web client ID)"
            )
        return cleaned

    @field_validator("JWT_SECRET")
    @classmethod
    def jwt_secret_must_be_strong(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if len(cleaned) < 32:
            raise ValueError(
                "JWT_SECRET must be set in backend/.env and be at least 32 characters"
            )
        return cleaned


settings = Settings()
