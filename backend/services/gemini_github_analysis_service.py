import logging

from google.genai import types
from pydantic import ValidationError

from core.config.settings import settings
from schemas.github_analysis_schema import GeminiGitHubRepoAnalysisPayload
from services.gemini_client import build_gemini_client, call_with_transient_retries
from services.gemini_config import get_gemini_api_key, get_gemini_model

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """You prepare users to discuss a PUBLIC GitHub repository in technical interviews.

Rules:
- Use ONLY evidence in the prompt: repo metadata, language stats, README text, file path sample.
- NEVER claim the user wrote all code or owns every commit.
- NEVER invent implementation details, tests, architecture, or security controls not evidenced.
- List unknowns explicitly when README/metadata are insufficient.
- frameworks_and_libraries: only if mentioned in README, topics, or path names — otherwise say unknown.
- interview_questions must map to evidence_basis citing what was inspected.
- Cover categories across questions: architecture, technology_selection, design_decisions,
  challenges, testing, performance, security, future_improvements when evidence allows.
- improvement_suggestions must be generic engineering advice, not fake audit findings.
- authorship_caveat must remind that public repo visibility does not prove sole authorship.
"""


class GitHubAnalysisGeminiError(Exception):
    pass


class GitHubAnalysisGeminiUnavailableError(GitHubAnalysisGeminiError):
    pass


def _build_prompt(
    *,
    full_name: str,
    metadata: dict,
    readme: str | None,
    languages: dict,
    tree_paths: list[str],
    inspection_notes: list[str],
) -> str:
    topics = ", ".join((metadata.get("topics") or [])[:15])
    return (
        f"Repository: {full_name}\n"
        f"Description: {metadata.get('description') or '(none)'}\n"
        f"Primary language field: {metadata.get('language')}\n"
        f"Topics: {topics or '(none)'}\n"
        f"Fork: {metadata.get('fork')}\n"
        f"Default branch: {metadata.get('default_branch')}\n"
        f"Language breakdown (bytes): {languages}\n\n"
        f"README (untrusted text, may be truncated):\n{(readme or '(missing)')[:14000]}\n\n"
        f"Sample file paths (structure hint only):\n"
        + "\n".join(tree_paths[:60])
        + "\n\n"
        f"Inspection notes:\n" + "\n".join(f"- {n}" for n in inspection_notes)
    )


def generate_github_repo_analysis(
    *,
    full_name: str,
    metadata: dict,
    readme: str | None,
    languages: dict,
    tree_paths: list[str],
    inspection_notes: list[str],
) -> GeminiGitHubRepoAnalysisPayload:
    api_key = get_gemini_api_key()
    model = get_gemini_model()
    client = build_gemini_client(api_key)

    def _call():
        return client.models.generate_content(
            model=model,
            contents=_build_prompt(
                full_name=full_name,
                metadata=metadata,
                readme=readme,
                languages=languages,
                tree_paths=tree_paths,
                inspection_notes=inspection_notes,
            ),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.3,
                response_mime_type="application/json",
                response_schema=GeminiGitHubRepoAnalysisPayload,
            ),
        )

    try:
        response = call_with_transient_retries(
            _call,
            max_attempts=max(int(settings.GEMINI_APP_RETRY_ATTEMPTS), 1),
            initial_delay=float(settings.GEMINI_RETRY_INITIAL_DELAY_SECONDS),
            max_delay=float(settings.GEMINI_RETRY_MAX_DELAY_SECONDS),
            operation_name="gemini_github_repo_analysis",
        )
    except Exception as exc:
        logger.warning("GitHub analysis generation failed: %s", type(exc).__name__)
        raise GitHubAnalysisGeminiUnavailableError("Analysis generation unavailable.") from exc

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise GitHubAnalysisGeminiError("Empty analysis response.")

    try:
        return GeminiGitHubRepoAnalysisPayload.model_validate_json(raw_text)
    except ValidationError as exc:
        raise GitHubAnalysisGeminiError("Invalid analysis structure.") from exc
