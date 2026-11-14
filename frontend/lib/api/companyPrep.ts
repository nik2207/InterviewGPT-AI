import { apiClient } from "@/lib/api/client";
import type {
  CompanyCatalogueListResponse,
  CompanyCatalogueEntry,
  CompanyPrepDetail,
  CompanyPrepListItem,
  ExperienceLevel,
  PrepCategory,
} from "@/types/companyPrep";

export async function searchCompanies(
  query?: string
): Promise<CompanyCatalogueListResponse> {
  const { data } = await apiClient.get<CompanyCatalogueListResponse>(
    "/company-prep/companies",
    { params: query ? { q: query } : undefined }
  );
  return data;
}

export async function fetchCompany(companyId: string): Promise<CompanyCatalogueEntry> {
  const { data } = await apiClient.get<CompanyCatalogueEntry>(
    `/company-prep/companies/${companyId}`
  );
  return data;
}

export async function createCompanyPreparation(payload: {
  company_id: string;
  job_role: string;
  experience_level: ExperienceLevel;
  categories: PrepCategory[];
  user_notes?: string;
}): Promise<CompanyPrepDetail> {
  const { data } = await apiClient.post<CompanyPrepDetail>(
    "/company-prep/preparations",
    payload
  );
  return data;
}

export async function fetchCompanyPreparations(): Promise<CompanyPrepListItem[]> {
  const { data } = await apiClient.get<{ preparations: CompanyPrepListItem[] }>(
    "/company-prep/preparations"
  );
  return data.preparations;
}

export async function fetchCompanyPreparation(
  prepId: string
): Promise<CompanyPrepDetail> {
  const { data } = await apiClient.get<CompanyPrepDetail>(
    `/company-prep/preparations/${prepId}`
  );
  return data;
}

export async function updateCompanyPrepChecklist(
  prepId: string,
  items: CompanyPrepDetail["checklist"]
): Promise<CompanyPrepDetail> {
  const { data } = await apiClient.patch<CompanyPrepDetail>(
    `/company-prep/preparations/${prepId}/checklist`,
    { items }
  );
  return data;
}

export async function startCompanyPrepInterview(
  prepId: string,
  payload: {
    resume_id?: string;
    question_count?: number;
    voice_interview_enabled?: boolean;
  }
): Promise<{ preparation_id: string; interview_session_id: string }> {
  const { data } = await apiClient.post<{
    preparation_id: string;
    interview_session_id: string;
  }>(`/company-prep/preparations/${prepId}/start-interview`, payload);
  return data;
}
