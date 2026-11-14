from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from core.dependencies import get_github_analysis_repository, get_session_repository, get_user_repository
from core.security.jwt import create_access_token
from schemas.github_analysis_schema import GeneratedRepoInterviewQuestion, GeminiGitHubRepoAnalysisPayload
from services.github_api_client import GitHubRateLimitError
from services.github_input_parser import GitHubInputError, parse_github_input
from tests.test_auth_routes import InMemorySessionRepository


class FakeGitHubAnalysisRepository:
    def __init__(self) -> None:
        self.get_cached_profile = AsyncMock(return_value=None)
        self.upsert_profile_cache = AsyncMock()
        self.create_analysis = AsyncMock()
        self.find_analysis_for_user = AsyncMock(return_value=None)
        self.list_analyses_for_user = AsyncMock(return_value=[])


@pytest.fixture
def github_client(client: TestClient, sample_user_document: dict):
    gh_repo = FakeGitHubAnalysisRepository()
    user_repo = AsyncMock()
    user_repo.find_by_id = AsyncMock(return_value=sample_user_document)

    from app.main import app

    session_repo = InMemorySessionRepository()
    app.dependency_overrides[get_github_analysis_repository] = lambda: gh_repo
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_session_repository] = lambda: session_repo

    token, _, _ = create_access_token(
        str(sample_user_document["_id"]),
        sample_user_document["email"],
    )
    headers = {"Authorization": f"Bearer {token}"}
    user_id = str(sample_user_document["_id"])
    yield client, gh_repo, headers, user_id
    app.dependency_overrides.clear()


def test_parse_username_and_url():
    assert parse_github_input("octocat") == ("octocat", None)
    assert parse_github_input("https://github.com/octocat/Hello-World") == (
        "octocat",
        "Hello-World",
    )


def test_parse_invalid_url():
    with pytest.raises(GitHubInputError):
        parse_github_input("https://gitlab.com/user/repo")


def test_parse_invalid_username():
    with pytest.raises(GitHubInputError):
        parse_github_input("-invalid")


def test_parse_empty_input():
    with pytest.raises(GitHubInputError):
        parse_github_input("   ")


@patch("services.github_analysis_service.fetch_user_repositories")
@patch("services.github_analysis_service.fetch_user_profile")
def test_lookup_success(mock_profile, mock_repos, github_client):
    client, gh_repo, headers, _ = github_client
    mock_profile.return_value = (
        {"login": "octocat", "name": "Octocat", "bio": "GitHub", "public_repos": 1},
        55,
    )
    mock_repos.return_value = (
        [
            {
                "full_name": "octocat/Hello-World",
                "name": "Hello-World",
                "owner": {"login": "octocat"},
                "description": "My first repo",
                "language": "C",
                "topics": [],
                "default_branch": "main",
                "stargazers_count": 100,
                "updated_at": "2024-01-01T00:00:00Z",
                "private": False,
                "fork": False,
            }
        ],
        54,
    )

    response = client.post(
        "/api/v1/github/lookup",
        headers=headers,
        json={"input_value": "octocat"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["owner"] == "octocat"
    assert len(body["repositories"]) == 1
    gh_repo.upsert_profile_cache.assert_awaited_once()


@patch("services.github_analysis_service.fetch_user_profile")
def test_lookup_rate_limit(mock_profile, github_client):
    client, _, headers, _ = github_client
    mock_profile.side_effect = GitHubRateLimitError("rate", status_code=429)

    response = client.post(
        "/api/v1/github/lookup",
        headers=headers,
        json={"input_value": "octocat"},
    )
    assert response.status_code == 429


@patch("services.github_analysis_service.generate_github_repo_analysis")
@patch("services.github_analysis_service.fetch_tree_paths")
@patch("services.github_analysis_service.fetch_languages")
@patch("services.github_analysis_service.fetch_readme_text")
@patch("services.github_analysis_service.fetch_repository")
def test_analyze_repository(
    mock_repo,
    mock_readme,
    mock_langs,
    mock_tree,
    mock_gemini,
    github_client,
):
    client, gh_repo, headers, user_id = github_client
    mock_repo.return_value = {
        "full_name": "octocat/Hello-World",
        "description": "Demo",
        "language": "Python",
        "topics": ["demo"],
        "fork": False,
        "default_branch": "main",
        "private": False,
    }
    mock_readme.return_value = "# Hello\n\nA sample project."
    mock_langs.return_value = {"Python": 1000.0}
    mock_tree.return_value = ["README.md", "src/app.py"]
    mock_gemini.return_value = GeminiGitHubRepoAnalysisPayload(
        project_description="Demo repository described in README for learning purposes.",
        main_languages=["Python"],
        frameworks_and_libraries=["Unknown — not in README"],
        structure_overview="README and src/ folder present in sampled paths.",
        key_modules=["src/app.py"],
        architecture_notes="Insufficient evidence for detailed architecture.",
        interview_questions=[
            GeneratedRepoInterviewQuestion(
                category="architecture",
                question="How would you describe the high-level layout based on the file paths?",
                evidence_basis="Path sample includes src/app.py",
            ),
            GeneratedRepoInterviewQuestion(
                category="technology_selection",
                question="Why might Python fit this README description?",
                evidence_basis="Languages API reports Python",
            ),
            GeneratedRepoInterviewQuestion(
                category="testing",
                question="What testing evidence is visible in the inspected paths?",
                evidence_basis="No test paths in sample",
            ),
            GeneratedRepoInterviewQuestion(
                category="security",
                question="What security topics would you clarify before claiming production readiness?",
                evidence_basis="README only; no security artifacts inspected",
            ),
        ],
        project_explanation_prep=["State what README claims vs unknowns"],
        improvement_suggestions=["Add tests documentation if missing"],
        demonstrable_skills=["Python"],
        authorship_caveat="Public visibility does not prove sole authorship.",
        unknowns=["Runtime behavior"],
    )

    now = datetime.now(timezone.utc)
    gh_repo.create_analysis = AsyncMock(
        return_value={
            "_id": ObjectId("507f1f77bcf86cd799439060"),
            "user_id": user_id,
            "owner": "octocat",
            "repo_full_name": "octocat/Hello-World",
            "status": "completed",
            "inspection": {
                "sources_inspected": ["repository metadata API"],
                "not_inspected": [],
                "readme_available": True,
                "readme_truncated": False,
                "readme_char_count": 10,
                "tree_paths_sampled": [],
                "languages_breakdown": {},
            },
            "result": mock_gemini.return_value.model_dump(),
            "error_message": None,
            "created_at": now,
        }
    )

    response = client.post(
        "/api/v1/github/analyses",
        headers=headers,
        json={
            "owner": "octocat",
            "repository_full_names": ["octocat/Hello-World"],
        },
    )
    assert response.status_code == 200
    analysis = response.json()["analyses"][0]
    assert analysis["status"] == "completed"
    assert analysis["result"]["authorship_caveat"]


@patch("services.github_analysis_service.generate_github_repo_analysis")
@patch("services.github_analysis_service.fetch_readme_text")
@patch("services.github_analysis_service.fetch_languages")
@patch("services.github_analysis_service.fetch_tree_paths")
@patch("services.github_analysis_service.fetch_repository")
def test_analyze_missing_readme(
    mock_repo,
    mock_tree,
    mock_langs,
    mock_readme,
    mock_gemini,
    github_client,
):
    client, gh_repo, headers, user_id = github_client
    mock_repo.return_value = {
        "full_name": "octocat/empty",
        "description": None,
        "language": None,
        "topics": [],
        "fork": False,
        "default_branch": "main",
        "private": False,
    }
    mock_readme.return_value = None
    mock_langs.return_value = {}
    mock_tree.return_value = []
    from services.gemini_github_analysis_service import GitHubAnalysisGeminiUnavailableError

    mock_gemini.side_effect = GitHubAnalysisGeminiUnavailableError("down")
    now = datetime.now(timezone.utc)
    gh_repo.create_analysis = AsyncMock(
        return_value={
            "_id": ObjectId(),
            "user_id": user_id,
            "owner": "octocat",
            "repo_full_name": "octocat/empty",
            "status": "failed",
            "inspection": {},
            "result": None,
            "error_message": "down",
            "created_at": now,
        }
    )

    response = client.post(
        "/api/v1/github/analyses",
        headers=headers,
        json={"owner": "octocat", "repository_full_names": ["octocat/empty"]},
    )
    assert response.status_code == 200
    assert response.json()["analyses"][0]["status"] == "failed"


def test_analysis_ownership_get(github_client):
    client, gh_repo, headers, user_id = github_client
    now = datetime.now(timezone.utc)
    gh_repo.find_analysis_for_user = AsyncMock(
        return_value={
            "_id": ObjectId("507f1f77bcf86cd799439061"),
            "user_id": user_id,
            "owner": "octocat",
            "repo_full_name": "octocat/Hello-World",
            "status": "completed",
            "inspection": {
                "sources_inspected": ["repository metadata API"],
                "not_inspected": [],
                "readme_available": False,
                "readme_truncated": False,
                "readme_char_count": 0,
                "tree_paths_sampled": [],
                "languages_breakdown": {},
            },
            "result": None,
            "error_message": None,
            "created_at": now,
        }
    )

    response = client.get(
        "/api/v1/github/analyses/507f1f77bcf86cd799439061",
        headers=headers,
    )
    assert response.status_code == 200
