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
    GEMINI_SDK_HTTP_ATTEMPTS: int = 4
    GEMINI_APP_RETRY_ATTEMPTS: int = 1
    GEMINI_RETRY_INITIAL_DELAY_SECONDS: float = 1.0
    GEMINI_RETRY_MAX_DELAY_SECONDS: float = 8.0

    INTERVIEW_MIN_QUESTIONS: int = 3
    INTERVIEW_MAX_QUESTIONS: int = 15
    INTERVIEW_MAX_ANSWER_CHARS: int = 8000
    INTERVIEW_MAX_QUESTION_TEXT_CHARS: int = 2000
    SPEECH_FILLER_WORDS: str = (
        "um,uh,like,actually,basically,literally,sort of,kind of,you know"
    )

    GITHUB_API_BASE: str = "https://api.github.com"
    GITHUB_TOKEN: str = ""
    GITHUB_MAX_README_CHARS: int = 24_000
    GITHUB_MAX_TREE_PATHS: int = 80
    GITHUB_MAX_REPOS_PER_LOOKUP: int = 50
    GITHUB_HTTP_TIMEOUT_SECONDS: float = 20.0
    GITHUB_METADATA_CACHE_MINUTES: int = 60

    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    RAZORPAY_PLAN_ID_PRO: str = ""
    RAZORPAY_PLAN_ID_PREMIUM: str = ""
    BILLING_DEV_CHECKOUT: bool = False
    PLATFORM_SUPER_ADMIN_EMAILS: str = ""

    @property
    def razorpay_configured(self) -> bool:
        return bool(
            self.RAZORPAY_KEY_ID.strip()
            and self.RAZORPAY_KEY_SECRET.strip()
        )

    @property
    def speech_filler_word_list(self) -> tuple[str, ...]:
        return tuple(
            item.strip()
            for item in self.SPEECH_FILLER_WORDS.split(",")
            if item.strip()
        )

    @property
    def cors_origins(self) -> list[str]:
        """Comma-separated allowed browser origins (e.g. local + Railway frontend URL)."""
        raw = self.CORS_ORIGIN.strip()
        if not raw:
            return ["http://localhost:3000"]
        return [part.strip() for part in raw.split(",") if part.strip()]

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
