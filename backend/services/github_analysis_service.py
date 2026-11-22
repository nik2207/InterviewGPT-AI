import asyncio
import logging
from bson import ObjectId

from core.config.settings import settings
from repositories.github_analysis_repository import (
    GitHubAnalysisRepository,
    GitHubAnalysisRepositoryError,
)
from schemas.github_analysis_schema import (
    GITHUB_ANALYSIS_DISCLAIMER,
    GitHubAnalysisBatchResponse,
    GitHubAnalysisDetailResponse,
    GitHubAnalysisListItem,
    GitHubAnalysisListResponse,
    GitHubProfileLookupResponse,
    GitHubPublicRepositorySummary,
    GitHubRepositoryAnalysisResult,
    GitHubLookupRequest,
    RepositoryInspectionRecord,
    RunGitHubAnalysisRequest,
)
from services.gemini_github_analysis_service import (
    GitHubAnalysisGeminiError,
    GitHubAnalysisGeminiUnavailableError,
    generate_github_repo_analysis,
)
from services.github_api_client import (
    GitHubApiError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    fetch_languages,
    fetch_readme_text,
    fetch_repository,
    fetch_tree_paths,
    fetch_user_profile,
    fetch_user_repositories,
    parse_github_datetime,
)
from services.github_input_parser import GitHubInputError, parse_github_input

logger = logging.getLogger(__name__)


class GitHubAnalysisServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _oid_str(value) -> str:
    if isinstance(value, ObjectId):
        return str(value)
    return str(value)


def _repo_summary(item: dict) -> GitHubPublicRepositorySummary | None:
    if item.get("private"):
        return None
    owner = (item.get("owner") or {}).get("login") or ""
    return GitHubPublicRepositorySummary(
        full_name=item.get("full_name") or f"{owner}/{item.get('name', '')}",
        name=item.get("name", ""),
        owner=owner,
        description=item.get("description"),
        primary_language=item.get("language"),
        topics=list(item.get("topics") or [])[:20],
        default_branch=item.get("default_branch"),
        stars=int(item.get("stargazers_count") or 0),
        updated_at=parse_github_datetime(item.get("updated_at")),
        is_fork=bool(item.get("fork")),
    )


def _summaries_from_cache(repos: list[dict]) -> list[GitHubPublicRepositorySummary]:
    summaries: list[GitHubPublicRepositorySummary] = []
    for item in repos:
        parsed = _repo_summary(item)
        if parsed:
            summaries.append(parsed)
    return summaries


async def lookup_github_profile(
    payload: GitHubLookupRequest,
    repo: GitHubAnalysisRepository,
) -> GitHubProfileLookupResponse:
    try:
        owner, single_repo = parse_github_input(payload.input_value)
    except GitHubInputError as exc:
        raise GitHubAnalysisServiceError(str(exc), status_code=422) from exc

    cached = await repo.get_cached_profile(
        owner, settings.GITHUB_METADATA_CACHE_MINUTES
    )
    rate_remaining: int | None = None

    if cached:
        repos_raw = cached.get("repositories", [])
        profile = cached.get("profile", {})
        summaries = _summaries_from_cache(repos_raw)
    else:
        try:
            profile, rate_remaining = await fetch_user_profile(owner)
            repos_raw, rate_remaining = await fetch_user_repositories(owner)
        except GitHubNotFoundError as exc:
            raise GitHubAnalysisServiceError(str(exc), status_code=404) from exc
        except GitHubRateLimitError as exc:
            raise GitHubAnalysisServiceError(str(exc), status_code=429) from exc
        except GitHubApiError as exc:
            raise GitHubAnalysisServiceError(str(exc), status_code=exc.status_code) from exc

        summaries = _summaries_from_cache(repos_raw)
        try:
            await repo.upsert_profile_cache(
                owner,
                {"profile": profile, "repositories": repos_raw},
            )
        except GitHubAnalysisRepositoryError:
            logger.warning("Profile cache write failed for %s", owner)

    if single_repo:
        summaries = [s for s in summaries if s.name.lower() == single_repo.lower()]
        if not summaries:
            try:
                metadata = await fetch_repository(owner, single_repo)
            except GitHubNotFoundError as exc:
                raise GitHubAnalysisServiceError(str(exc), status_code=404) from exc
            except GitHubRateLimitError as exc:
                raise GitHubAnalysisServiceError(str(exc), status_code=429) from exc
            except GitHubApiError as exc:
                raise GitHubAnalysisServiceError(str(exc), status_code=exc.status_code) from exc
            parsed = _repo_summary(metadata)
            if parsed:
                summaries = [parsed]

    return GitHubProfileLookupResponse(
        owner=owner,
        profile_name=profile.get("name"),
        profile_url=f"https://github.com/{owner}",
        bio=profile.get("bio"),
        public_repos=int(profile.get("public_repos") or len(summaries)),
        repositories=summaries,
        cached=cached is not None,
        rate_limit_remaining=rate_remaining,
        disclaimer=GITHUB_ANALYSIS_DISCLAIMER,
    )


async def _inspect_repository(owner: str, repo_name: str) -> tuple[dict, RepositoryInspectionRecord, str | None]:
    try:
        metadata = await fetch_repository(owner, repo_name)
    except GitHubApiError as exc:
        raise GitHubAnalysisServiceError(str(exc), status_code=exc.status_code) from exc

    readme = await fetch_readme_text(owner, repo_name)
    languages = await fetch_languages(owner, repo_name)
    tree_paths = await fetch_tree_paths(owner, repo_name, metadata.get("default_branch"))

    inspected = ["repository metadata API", "languages API"]
    not_inspected = ["source code execution", "dependency lockfiles (full parse)", "commit history authorship"]
    readme_truncated = False
    readme_len = len(readme or "")
    if readme:
        inspected.append("README (raw text)")
        if readme_len >= settings.GITHUB_MAX_README_CHARS:
            readme_truncated = True
            not_inspected.append("full README beyond size cap")
    else:
        not_inspected.append("README content")

    if tree_paths:
        inspected.append("git tree path sample")
    else:
        not_inspected.append("recursive directory tree")

    inspection = RepositoryInspectionRecord(
        sources_inspected=inspected,
        not_inspected=not_inspected,
        readme_available=bool(readme),
        readme_truncated=readme_truncated,
        readme_char_count=readme_len,
        tree_paths_sampled=tree_paths,
        languages_breakdown=languages,
    )
    return metadata, inspection, readme


async def run_github_analyses(
    user_id: str,
    payload: RunGitHubAnalysisRequest,
    repository: GitHubAnalysisRepository,
) -> GitHubAnalysisBatchResponse:
    owner = payload.owner.strip().lower()
    results: list[GitHubAnalysisDetailResponse] = []

    for full_name in payload.repository_full_names:
        if "/" not in full_name:
            raise GitHubAnalysisServiceError(
                f"Invalid repository name: {full_name}", status_code=422
            )
        repo_owner, repo_name = full_name.split("/", 1)
        if repo_owner.lower() != owner:
            raise GitHubAnalysisServiceError(
                "All repositories must belong to the selected owner.",
                status_code=422,
            )

        try:
            metadata, inspection, readme = await _inspect_repository(repo_owner, repo_name)
        except GitHubAnalysisServiceError as exc:
            saved = await _save_failed_analysis(
                repository, user_id, owner, full_name, str(exc), inspection=None
            )
            results.append(saved)
            continue

        inspection_notes = inspection.sources_inspected + [
            f"not inspected: {item}" for item in inspection.not_inspected
        ]

        try:
            gemini = await asyncio.to_thread(
                generate_github_repo_analysis,
                full_name=full_name,
                metadata=metadata,
                readme=readme,
                languages=inspection.languages_breakdown,
                tree_paths=inspection.tree_paths_sampled,
                inspection_notes=inspection_notes,
            )
            result = GitHubRepositoryAnalysisResult.model_validate(gemini.model_dump())
            saved_doc = await repository.create_analysis(
                {
                    "user_id": user_id,
                    "owner": owner,
                    "repo_full_name": full_name,
                    "status": "completed",
                    "inspection": inspection.model_dump(),
                    "result": result.model_dump(),
                    "error_message": None,
                }
            )
            results.append(_detail_from_doc(saved_doc))
        except GitHubAnalysisGeminiUnavailableError as exc:
            saved = await _save_failed_analysis(
                repository, user_id, owner, full_name, str(exc), inspection
            )
            results.append(saved)
        except GitHubAnalysisGeminiError as exc:
            saved = await _save_failed_analysis(
                repository, user_id, owner, full_name, str(exc), inspection
            )
            results.append(saved)

    return GitHubAnalysisBatchResponse(analyses=results)


async def _save_failed_analysis(
    repository: GitHubAnalysisRepository,
    user_id: str,
    owner: str,
    full_name: str,
    message: str,
    inspection: RepositoryInspectionRecord | None,
) -> GitHubAnalysisDetailResponse:
    try:
        saved = await repository.create_analysis(
            {
                "user_id": user_id,
                "owner": owner,
                "repo_full_name": full_name,
                "status": "failed",
                "inspection": inspection.model_dump() if inspection else {},
                "result": None,
                "error_message": message,
            }
        )
    except GitHubAnalysisRepositoryError:
        raise GitHubAnalysisServiceError("Failed to persist analysis.", status_code=500) from None
    return _detail_from_doc(saved)


def _detail_from_doc(document: dict) -> GitHubAnalysisDetailResponse:
    inspection_raw = document.get("inspection") or {}
    inspection = (
        RepositoryInspectionRecord.model_validate(inspection_raw)
        if inspection_raw
        else RepositoryInspectionRecord()
    )
    result_raw = document.get("result")
    result = (
        GitHubRepositoryAnalysisResult.model_validate(result_raw)
        if result_raw
        else None
    )
    return GitHubAnalysisDetailResponse(
        id=_oid_str(document["_id"]),
        user_id=document["user_id"],
        owner=document["owner"],
        repo_full_name=document["repo_full_name"],
        status=document.get("status", "failed"),
        inspection=inspection,
        result=result,
        error_message=document.get("error_message"),
        disclaimer=GITHUB_ANALYSIS_DISCLAIMER,
        created_at=document["created_at"],
    )


async def list_github_analyses(
    user_id: str,
    repository: GitHubAnalysisRepository,
) -> GitHubAnalysisListResponse:
    docs = await repository.list_analyses_for_user(user_id)
    items: list[GitHubAnalysisListItem] = []
    for doc in docs:
        lang = None
        if doc.get("result"):
            langs = doc["result"].get("main_languages") or []
            lang = langs[0] if langs else None
        items.append(
            GitHubAnalysisListItem(
                id=_oid_str(doc["_id"]),
                owner=doc["owner"],
                repo_full_name=doc["repo_full_name"],
                status=doc.get("status", "failed"),
                created_at=doc["created_at"],
                primary_language=lang,
            )
        )
    return GitHubAnalysisListResponse(analyses=items)


async def get_github_analysis(
    user_id: str,
    analysis_id: str,
    repository: GitHubAnalysisRepository,
) -> GitHubAnalysisDetailResponse:
    doc = await repository.find_analysis_for_user(analysis_id, user_id)
    if doc is None:
        raise GitHubAnalysisServiceError("Analysis not found.", status_code=404)
    return _detail_from_doc(doc)
