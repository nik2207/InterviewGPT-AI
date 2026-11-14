import { apiClient } from "@/lib/api/client";
import type {
  ResumeAiProposal,
  ResumeBuilderContent,
  ResumeBuilderDetail,
  ResumeBuilderListItem,
  ResumeBuilderTemplate,
} from "@/types/resumeBuilder";

export async function listResumeBuilders(): Promise<ResumeBuilderListItem[]> {
  const { data } = await apiClient.get<{ items: ResumeBuilderListItem[] }>(
    "/resume-builder"
  );
  return data.items;
}

export async function createResumeBuilder(payload: {
  title?: string;
  template?: ResumeBuilderTemplate;
  source_upload_resume_id?: string;
}): Promise<ResumeBuilderDetail> {
  const { data } = await apiClient.post<ResumeBuilderDetail>(
    "/resume-builder",
    payload
  );
  return data;
}

export async function fetchResumeBuilder(id: string): Promise<ResumeBuilderDetail> {
  const { data } = await apiClient.get<ResumeBuilderDetail>(`/resume-builder/${id}`);
  return data;
}

export async function updateResumeBuilder(
  id: string,
  payload: {
    title?: string;
    template?: ResumeBuilderTemplate;
    section_order?: string[];
    content?: ResumeBuilderContent;
  }
): Promise<ResumeBuilderDetail> {
  const { data } = await apiClient.patch<ResumeBuilderDetail>(
    `/resume-builder/${id}`,
    payload
  );
  return data;
}

export async function saveResumeBuilderVersion(
  id: string,
  label: string
): Promise<ResumeBuilderDetail> {
  const { data } = await apiClient.post<ResumeBuilderDetail>(
    `/resume-builder/${id}/versions`,
    { label }
  );
  return data;
}

export async function downloadResumeBuilderPdf(id: string): Promise<Blob> {
  const { data } = await apiClient.get<Blob>(`/resume-builder/${id}/pdf`, {
    responseType: "blob",
  });
  return data;
}

export async function deleteResumeBuilder(id: string): Promise<void> {
  await apiClient.delete(`/resume-builder/${id}`);
}

export async function aiImproveSummary(id: string): Promise<ResumeAiProposal> {
  const { data } = await apiClient.post<ResumeAiProposal>(
    `/resume-builder/${id}/ai/improve-summary`
  );
  return data;
}

export async function aiImproveBullets(
  id: string,
  experienceId: string,
  section: "work_experience" | "internships"
): Promise<ResumeAiProposal> {
  const { data } = await apiClient.post<ResumeAiProposal>(
    `/resume-builder/${id}/ai/improve-bullets`,
    { experience_id: experienceId, section }
  );
  return data;
}

export async function aiImproveProject(
  id: string,
  projectId: string
): Promise<ResumeAiProposal> {
  const { data } = await apiClient.post<ResumeAiProposal>(
    `/resume-builder/${id}/ai/improve-project`,
    { project_id: projectId }
  );
  return data;
}

export async function aiMissingInfo(id: string): Promise<ResumeAiProposal> {
  const { data } = await apiClient.post<ResumeAiProposal>(
    `/resume-builder/${id}/ai/missing-info`
  );
  return data;
}

export async function aiJobKeywords(
  id: string,
  jobDescription: string
): Promise<ResumeAiProposal> {
  const { data } = await apiClient.post<ResumeAiProposal>(
    `/resume-builder/${id}/ai/job-keywords`,
    { job_description: jobDescription }
  );
  return data;
}

export async function aiAtsFormatting(id: string): Promise<ResumeAiProposal> {
  const { data } = await apiClient.post<ResumeAiProposal>(
    `/resume-builder/${id}/ai/ats-formatting`
  );
  return data;
}
