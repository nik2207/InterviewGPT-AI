import { apiClient } from "@/lib/api/client";
import type {
  CreateJobMatchPayload,
  JobMatchListItem,
  JobMatchResult,
} from "@/types/jobMatch";

export async function createJobMatch(
  payload: CreateJobMatchPayload
): Promise<JobMatchResult> {
  const { data } = await apiClient.post<JobMatchResult>("/job-matches", payload);
  return data;
}

export async function fetchJobMatches(): Promise<JobMatchListItem[]> {
  const { data } = await apiClient.get<{ matches: JobMatchListItem[] }>(
    "/job-matches"
  );
  return data.matches;
}

export async function fetchJobMatch(matchId: string): Promise<JobMatchResult> {
  const { data } = await apiClient.get<JobMatchResult>(`/job-matches/${matchId}`);
  return data;
}
