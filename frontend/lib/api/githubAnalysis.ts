import { apiClient } from "@/lib/api/client";
import type {
  GitHubAnalysisDetail,
  GitHubAnalysisListItem,
  GitHubProfileLookupResponse,
} from "@/types/githubAnalysis";

export async function lookupGitHubProfile(
  inputValue: string
): Promise<GitHubProfileLookupResponse> {
  const { data } = await apiClient.post<GitHubProfileLookupResponse>(
    "/github/lookup",
    { input_value: inputValue }
  );
  return data;
}

export async function runGitHubAnalyses(
  owner: string,
  repositoryFullNames: string[]
): Promise<GitHubAnalysisDetail[]> {
  const { data } = await apiClient.post<{ analyses: GitHubAnalysisDetail[] }>(
    "/github/analyses",
    { owner, repository_full_names: repositoryFullNames }
  );
  return data.analyses;
}

export async function fetchGitHubAnalyses(): Promise<GitHubAnalysisListItem[]> {
  const { data } = await apiClient.get<{ analyses: GitHubAnalysisListItem[] }>(
    "/github/analyses"
  );
  return data.analyses;
}

export async function fetchGitHubAnalysis(id: string): Promise<GitHubAnalysisDetail> {
  const { data } = await apiClient.get<GitHubAnalysisDetail>(`/github/analyses/${id}`);
  return data;
}
