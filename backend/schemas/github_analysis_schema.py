from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

GITHUB_ANALYSIS_DISCLAIMER = (
    "Analysis is based on public GitHub metadata and README text only. "
    "We do not run or download repository code. We cannot confirm you authored "
    "every commit or file. Generated questions are practice prompts, not facts "
    "about the implementation."
)

InterviewQuestionCategory = Literal[
    "architecture",
    "technology_selection",
    "design_decisions",
    "challenges",
    "testing",
    "performance",
    "security",
    "future_improvements",
]


class GitHubLookupRequest(BaseModel):
    input_value: str = Field(..., min_length=1, max_length=300)


class GitHubPublicRepositorySummary(BaseModel):
    full_name: str
    name: str
    owner: str
    description: str | None = None
    primary_language: str | None = None
    topics: list[str] = Field(default_factory=list, max_length=20)
    default_branch: str | None = None
    stars: int = 0
    updated_at: datetime | None = None
    is_fork: bool = False


class GitHubProfileLookupResponse(BaseModel):
    owner: str
    profile_name: str | None = None
    profile_url: str
    bio: str | None = None
    public_repos: int
    repositories: list[GitHubPublicRepositorySummary]
    disclaimer: str = GITHUB_ANALYSIS_DISCLAIMER
    cached: bool = False
    rate_limit_remaining: int | None = None


class RunGitHubAnalysisRequest(BaseModel):
    owner: str = Field(..., min_length=1, max_length=80)
    repository_full_names: list[str] = Field(..., min_length=1, max_length=10)

    @field_validator("repository_full_names")
    @classmethod
    def unique_repos(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in value:
            cleaned = item.strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                ordered.append(cleaned)
        return ordered


class RepositoryInspectionRecord(BaseModel):
    sources_inspected: list[str] = Field(default_factory=list, max_length=20)
    not_inspected: list[str] = Field(default_factory=list, max_length=20)
    readme_available: bool = False
    readme_truncated: bool = False
    readme_char_count: int = 0
    tree_paths_sampled: list[str] = Field(default_factory=list, max_length=80)
    languages_breakdown: dict[str, float] = Field(default_factory=dict)


class GeneratedRepoInterviewQuestion(BaseModel):
    category: InterviewQuestionCategory
    question: str = Field(..., min_length=5, max_length=500)
    evidence_basis: str = Field(..., min_length=5, max_length=500)


class GitHubRepositoryAnalysisResult(BaseModel):
    project_description: str
    main_languages: list[str] = Field(default_factory=list, max_length=15)
    frameworks_and_libraries: list[str] = Field(default_factory=list, max_length=25)
    structure_overview: str
    key_modules: list[str] = Field(default_factory=list, max_length=20)
    architecture_notes: str
    interview_questions: list[GeneratedRepoInterviewQuestion] = Field(
        default_factory=list, max_length=20
    )
    project_explanation_prep: list[str] = Field(default_factory=list, max_length=12)
    improvement_suggestions: list[str] = Field(default_factory=list, max_length=12)
    demonstrable_skills: list[str] = Field(default_factory=list, max_length=20)
    authorship_caveat: str
    unknowns: list[str] = Field(default_factory=list, max_length=15)


class GitHubAnalysisListItem(BaseModel):
    id: str
    owner: str
    repo_full_name: str
    status: Literal["completed", "failed"]
    created_at: datetime
    primary_language: str | None = None


class GitHubAnalysisListResponse(BaseModel):
    analyses: list[GitHubAnalysisListItem]
    disclaimer: str = GITHUB_ANALYSIS_DISCLAIMER


class GitHubAnalysisDetailResponse(BaseModel):
    id: str
    user_id: str
    owner: str
    repo_full_name: str
    status: Literal["completed", "failed"]
    inspection: RepositoryInspectionRecord
    result: GitHubRepositoryAnalysisResult | None = None
    error_message: str | None = None
    disclaimer: str = GITHUB_ANALYSIS_DISCLAIMER
    created_at: datetime


class GitHubAnalysisBatchResponse(BaseModel):
    analyses: list[GitHubAnalysisDetailResponse]
    disclaimer: str = GITHUB_ANALYSIS_DISCLAIMER


class GeminiGitHubRepoAnalysisPayload(BaseModel):
    project_description: str = Field(..., min_length=10, max_length=2000)
    main_languages: list[str] = Field(default_factory=list, max_length=15)
    frameworks_and_libraries: list[str] = Field(default_factory=list, max_length=25)
    structure_overview: str = Field(..., min_length=10, max_length=3000)
    key_modules: list[str] = Field(default_factory=list, max_length=20)
    architecture_notes: str = Field(..., min_length=10, max_length=3000)
    interview_questions: list[GeneratedRepoInterviewQuestion] = Field(
        default_factory=list, min_length=4, max_length=16
    )
    project_explanation_prep: list[str] = Field(default_factory=list, max_length=12)
    improvement_suggestions: list[str] = Field(default_factory=list, max_length=12)
    demonstrable_skills: list[str] = Field(default_factory=list, max_length=20)
    authorship_caveat: str = Field(..., min_length=20, max_length=800)
    unknowns: list[str] = Field(default_factory=list, max_length=15)
