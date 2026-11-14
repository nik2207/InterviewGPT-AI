export interface GitHubPublicRepositorySummary {
  full_name: string;
  name: string;
  owner: string;
  description: string | null;
  primary_language: string | null;
  topics: string[];
  default_branch: string | null;
  stars: number;
  updated_at: string | null;
  is_fork: boolean;
}

export interface GitHubProfileLookupResponse {
  owner: string;
  profile_name: string | null;
  profile_url: string;
  bio: string | null;
  public_repos: number;
  repositories: GitHubPublicRepositorySummary[];
  disclaimer: string;
  cached: boolean;
  rate_limit_remaining: number | null;
}

export interface RepositoryInspectionRecord {
  sources_inspected: string[];
  not_inspected: string[];
  readme_available: boolean;
  readme_truncated: boolean;
  readme_char_count: number;
  tree_paths_sampled: string[];
  languages_breakdown: Record<string, number>;
}

export interface GeneratedRepoInterviewQuestion {
  category: string;
  question: string;
  evidence_basis: string;
}

export interface GitHubRepositoryAnalysisResult {
  project_description: string;
  main_languages: string[];
  frameworks_and_libraries: string[];
  structure_overview: string;
  key_modules: string[];
  architecture_notes: string;
  interview_questions: GeneratedRepoInterviewQuestion[];
  project_explanation_prep: string[];
  improvement_suggestions: string[];
  demonstrable_skills: string[];
  authorship_caveat: string;
  unknowns: string[];
}

export interface GitHubAnalysisDetail {
  id: string;
  user_id: string;
  owner: string;
  repo_full_name: string;
  status: "completed" | "failed";
  inspection: RepositoryInspectionRecord;
  result: GitHubRepositoryAnalysisResult | null;
  error_message: string | null;
  disclaimer: string;
  created_at: string;
}

export interface GitHubAnalysisListItem {
  id: string;
  owner: string;
  repo_full_name: string;
  status: "completed" | "failed";
  created_at: string;
  primary_language: string | null;
}
