from google.auth.transport import requests
from google.oauth2 import id_token

from core.config.settings import settings

GOOGLE_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})


class GoogleTokenError(Exception):
    """Raised when a Google ID token fails verification."""


def verify_google_token(token: str) -> dict:
    """
    Verify a Google OAuth ID token (not a Google access token).
    Returns verified claims including sub, email, name, and picture.
    """
    if token is None or not str(token).strip():
        raise GoogleTokenError("Google ID token is required")

    cleaned = str(token).strip()

    try:
        claims = id_token.verify_oauth2_token(
            cleaned,
            requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError as exc:
        raise GoogleTokenError("Invalid Google ID token") from exc

    issuer = claims.get("iss")
    if issuer not in GOOGLE_ISSUERS:
        raise GoogleTokenError("Invalid Google ID token issuer")

    audience = claims.get("aud")
    if audience != settings.GOOGLE_CLIENT_ID:
        raise GoogleTokenError("Invalid Google ID token audience")

    if not claims.get("sub"):
        raise GoogleTokenError("Invalid Google ID token subject")

    if not claims.get("email"):
        raise GoogleTokenError("Google account email is required")

    return claims
