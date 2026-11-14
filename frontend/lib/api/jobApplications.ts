import { apiClient } from "@/lib/api/client";
import type {
  CreateJobApplicationPayload,
  JobApplication,
  JobApplicationListResponse,
  JobApplicationStats,
  UpdateJobApplicationPayload,
} from "@/types/jobApplication";

export interface ListApplicationsParams {
  status?: string;
  q?: string;
  employment_type?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_dir?: number;
}

export async function fetchApplications(
  params: ListApplicationsParams = {}
): Promise<JobApplicationListResponse> {
  const { data } = await apiClient.get<JobApplicationListResponse>(
    "/applications",
    { params }
  );
  return data;
}

export async function fetchApplicationStats(): Promise<JobApplicationStats> {
  const { data } = await apiClient.get<JobApplicationStats>("/applications/stats");
  return data;
}

export async function fetchApplication(appId: string): Promise<JobApplication> {
  const { data } = await apiClient.get<JobApplication>(`/applications/${appId}`);
  return data;
}

export async function createApplication(
  payload: CreateJobApplicationPayload
): Promise<JobApplication> {
  const { data } = await apiClient.post<JobApplication>("/applications", payload);
  return data;
}

export async function updateApplication(
  appId: string,
  payload: UpdateJobApplicationPayload
): Promise<JobApplication> {
  const { data } = await apiClient.patch<JobApplication>(
    `/applications/${appId}`,
    payload
  );
  return data;
}

export async function deleteApplication(appId: string): Promise<void> {
  await apiClient.delete(`/applications/${appId}`);
}

export async function startApplicationPractice(
  appId: string,
  options?: { resume_id?: string; question_count?: number }
): Promise<{ application_id: string; interview_session_id: string }> {
  const { data } = await apiClient.post<{
    application_id: string;
    interview_session_id: string;
  }>(`/applications/${appId}/start-practice`, {
    question_count: options?.question_count ?? 5,
    resume_id: options?.resume_id,
  });
  return data;
}
