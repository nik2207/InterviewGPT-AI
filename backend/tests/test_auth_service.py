from unittest.mock import patch

import pytest

from services.auth_service import GoogleTokenError, verify_google_token


def test_verify_google_token_missing():
    with pytest.raises(GoogleTokenError, match="required"):
        verify_google_token("")


def test_verify_google_token_malformed():
    with patch("services.auth_service.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.side_effect = ValueError("bad token")
        with pytest.raises(GoogleTokenError, match="Invalid Google ID token"):
            verify_google_token("not-a-real-token")


def test_verify_google_token_invalid_issuer():
    with patch("services.auth_service.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.return_value = {
            "iss": "evil-issuer",
            "sub": "x",
            "email": "a@b.com",
            "aud": "test-client-id.apps.googleusercontent.com",
        }
        with pytest.raises(GoogleTokenError, match="issuer"):
            verify_google_token("token")


def test_verify_google_token_wrong_audience():
    with patch("services.auth_service.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.return_value = {
            "iss": "https://accounts.google.com",
            "sub": "x",
            "email": "a@b.com",
            "aud": "wrong-audience",
        }
        with pytest.raises(GoogleTokenError, match="audience"):
            verify_google_token("token")


def test_verify_google_token_success(sample_google_claims):
    with patch("services.auth_service.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.return_value = sample_google_claims
        claims = verify_google_token("valid-token")
        assert claims["sub"] == sample_google_claims["sub"]
        assert claims["email"] == sample_google_claims["email"]
