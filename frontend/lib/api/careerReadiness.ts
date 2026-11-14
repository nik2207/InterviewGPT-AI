import { apiClient } from "@/lib/api/client";
import { getAccessToken } from "@/lib/auth-storage";
import type {
  CareerReadinessListItem,
  CareerReadinessReport,
} from "@/types/careerReadiness";

const baseURL = process.env.NEXT_PUBLIC_API_URL;

export async function generateCareerReadinessReport(payload: {
  resume_id: string;
  job_match_id?: string;
}): Promise<CareerReadinessReport> {
  const { data } = await apiClient.post<CareerReadinessReport>(
    "/career-readiness/reports",
    payload
  );
  return data;
}

export async function fetchCareerReadinessReports(): Promise<
  CareerReadinessListItem[]
> {
  const { data } = await apiClient.get<{ reports: CareerReadinessListItem[] }>(
    "/career-readiness/reports"
  );
  return data.reports;
}

export async function fetchCareerReadinessReport(
  reportId: string
): Promise<CareerReadinessReport> {
  const { data } = await apiClient.get<CareerReadinessReport>(
    `/career-readiness/reports/${reportId}`
  );
  return data;
}

export async function downloadCareerReadinessPdf(reportId: string): Promise<Blob> {
  const token = getAccessToken();
  const response = await fetch(
    `${baseURL}/career-readiness/reports/${reportId}/pdf`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    }
  );
  if (!response.ok) {
    throw new Error("PDF download failed");
  }
  return response.blob();
}
