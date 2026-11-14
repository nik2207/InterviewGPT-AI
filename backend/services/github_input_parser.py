import re
from urllib.parse import urlparse

GITHUB_USER_PATTERN = re.compile(
    r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$"
)


class GitHubInputError(Exception):
    pass


def parse_github_input(raw: str) -> tuple[str, str | None]:
    """Return (owner_login, repo_name or None for profile-only)."""
    value = (raw or "").strip()
    if not value:
        raise GitHubInputError("GitHub username or URL is required.")

    if "github.com" in value.lower():
        parsed = urlparse(value if "://" in value else f"https://{value}")
        if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
            raise GitHubInputError("Only github.com URLs are supported.")
        parts = [segment for segment in parsed.path.split("/") if segment]
        if len(parts) < 1:
            raise GitHubInputError("Invalid GitHub URL.")
        owner = parts[0]
        repo = parts[1] if len(parts) >= 2 else None
        if repo and repo.lower() in {"tree", "blob", "pull", "issues", "settings"}:
            raise GitHubInputError("Provide a repository root URL, not a sub-page.")
        _validate_username(owner)
        if repo:
            _validate_repo_name(repo)
        return owner, repo

    if "/" in value:
        owner, repo = value.split("/", 1)
        _validate_username(owner.strip())
        _validate_repo_name(repo.strip())
        return owner.strip(), repo.strip()

    _validate_username(value)
    return value, None


def _validate_username(username: str) -> None:
    if not GITHUB_USER_PATTERN.match(username):
        raise GitHubInputError("Invalid GitHub username format.")


def _validate_repo_name(repo: str) -> None:
    if not re.match(r"^[a-zA-Z0-9._-]+$", repo) or len(repo) > 100:
        raise GitHubInputError("Invalid repository name.")
