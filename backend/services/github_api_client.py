import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from core.config.settings import settings

logger = logging.getLogger(__name__)


class GitHubApiError(Exception):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class GitHubRateLimitError(GitHubApiError):
    pass


class GitHubNotFoundError(GitHubApiError):
    pass


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "InterviewGPT-Profile-Analyzer",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = (settings.GITHUB_TOKEN or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _parse_rate_limit(response: httpx.Response) -> int | None:
    raw = response.headers.get("X-RateLimit-Remaining")
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _handle_response(response: httpx.Response) -> Any:
    remaining = _parse_rate_limit(response)
    if response.status_code == 404:
        raise GitHubNotFoundError("GitHub resource not found.", status_code=404)
    if response.status_code == 403 and remaining == 0:
        raise GitHubRateLimitError(
            "GitHub API rate limit reached. Try again later.",
            status_code=429,
        )
    if response.status_code >= 400:
        raise GitHubApiError(
            "GitHub API request failed.",
            status_code=502 if response.status_code >= 500 else response.status_code,
        )
    if response.status_code == 204:
        return None
    return response.json()


async def fetch_user_profile(owner: str) -> tuple[dict, int | None]:
    url = f"{settings.GITHUB_API_BASE.rstrip('/')}/users/{owner}"
    async with httpx.AsyncClient(timeout=settings.GITHUB_HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(url, headers=_headers())
        remaining = _parse_rate_limit(response)
        data = _handle_response(response)
        return data, remaining


async def fetch_user_repositories(owner: str) -> tuple[list[dict], int | None]:
    url = f"{settings.GITHUB_API_BASE.rstrip('/')}/users/{owner}/repos"
    params = {
        "per_page": min(settings.GITHUB_MAX_REPOS_PER_LOOKUP, 100),
        "sort": "updated",
        "type": "public",
    }
    async with httpx.AsyncClient(timeout=settings.GITHUB_HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(url, headers=_headers(), params=params)
        remaining = _parse_rate_limit(response)
        data = _handle_response(response)
        if not isinstance(data, list):
            return [], remaining
        public_only = [item for item in data if not item.get("private", False)]
        return public_only[: settings.GITHUB_MAX_REPOS_PER_LOOKUP], remaining


async def fetch_repository(owner: str, repo: str) -> dict:
    url = f"{settings.GITHUB_API_BASE.rstrip('/')}/repos/{owner}/{repo}"
    async with httpx.AsyncClient(timeout=settings.GITHUB_HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(url, headers=_headers())
        data = _handle_response(response)
        if data.get("private"):
            raise GitHubApiError("Private repositories cannot be analyzed.", status_code=403)
        return data


async def fetch_readme_text(owner: str, repo: str) -> str | None:
    url = f"{settings.GITHUB_API_BASE.rstrip('/')}/repos/{owner}/{repo}/readme"
    headers = {**_headers(), "Accept": "application/vnd.github.raw"}
    async with httpx.AsyncClient(timeout=settings.GITHUB_HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            _handle_response(response)
        content_type = response.headers.get("content-type", "")
        if "text" not in content_type and "json" not in content_type:
            return None
        text = response.text or ""
        limit = settings.GITHUB_MAX_README_CHARS
        if len(text) > limit:
            return text[:limit]
        return text


async def fetch_languages(owner: str, repo: str) -> dict[str, float]:
    url = f"{settings.GITHUB_API_BASE.rstrip('/')}/repos/{owner}/{repo}/languages"
    async with httpx.AsyncClient(timeout=settings.GITHUB_HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(url, headers=_headers())
        if response.status_code == 404:
            return {}
        data = _handle_response(response)
        return data if isinstance(data, dict) else {}


async def fetch_tree_paths(owner: str, repo: str, branch: str | None) -> list[str]:
    if not branch:
        return []
    url = (
        f"{settings.GITHUB_API_BASE.rstrip('/')}/repos/{owner}/{repo}/git/trees/{branch}"
    )
    params = {"recursive": "1"}
    async with httpx.AsyncClient(timeout=settings.GITHUB_HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(url, headers=_headers(), params=params)
        if response.status_code == 404:
            return []
        if response.status_code >= 400:
            return []
        data = response.json()
        tree = data.get("tree") or []
        paths: list[str] = []
        for item in tree:
            if item.get("type") != "blob":
                continue
            path = item.get("path")
            if isinstance(path, str):
                paths.append(path)
            if len(paths) >= settings.GITHUB_MAX_TREE_PATHS:
                break
        return paths


def parse_github_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except ValueError:
        return None
