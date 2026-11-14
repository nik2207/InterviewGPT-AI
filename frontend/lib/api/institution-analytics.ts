import { apiClient } from "@/lib/api/client";

export interface InstitutionAnalyticsDashboard {
  institution_id: string;
  reporting_period: { from: string | null; to: string | null; generated_at: string };
  disclaimer: string;
  not_hiring_outcome_note: string;
  total_enrolled_students: number;
  active_students: number | null;
  practice_sessions_completed: number;
  average_interview_score: number | null;
  assignment_completion_rate: number;
  preparation_plan_completion_rate: number | null;
  skill_distribution: Record<string, number>;
  common_skill_gaps: Array<{ concept: string; mention_count: number }>;
  monthly_activity_trend: Array<{
    period: string;
    sessions: number;
    average_score: number | null;
  }>;
  cohort_comparisons: Array<{
    cohort_id: string;
    cohort_name: string;
    sample_size: number;
    sessions_completed: number | null;
    average_score: number | null;
    assignment_completion_rate: number | null;
    suppressed: boolean;
  }>;
  cards: Array<{
    label: string;
    value: string | number | null;
    sample_size: number | null;
    suppressed: boolean;
    note: string;
  }>;
}

export async function fetchInstitutionAnalyticsDashboard(
  institutionId: string,
  filters: {
    department?: string;
    course?: string;
    batch_label?: string;
    cohort_id?: string;
    job_role?: string;
    date_from?: string;
    date_to?: string;
  } = {}
) {
  const { data } = await apiClient.get<InstitutionAnalyticsDashboard>(
    `/institutions/${institutionId}/analytics/dashboard`,
    { params: filters }
  );
  return data;
}

export async function fetchInstitutionSubscription(institutionId: string) {
  const { data } = await apiClient.get(`/institutions/${institutionId}/admin/subscription`);
  return data as {
    subscription_plan: string;
    seat_limit: number;
    seats_used: number;
    features: string[];
    disclaimer: string;
  };
}

export async function fetchInstitutionAuditLog(institutionId: string, page = 1) {
  const { data } = await apiClient.get(
    `/institutions/${institutionId}/admin/audit`,
    { params: { page, page_size: 25 } }
  );
  return data as { items: Array<{ action: string; created_at: string; actor_user_id: string }>; total: number };
}

export async function fetchAdminMembers(institutionId: string, page = 1) {
  const { data } = await apiClient.get(`/institutions/${institutionId}/admin/members`, {
    params: { page, page_size: 25 },
  });
  return data as { items: Array<Record<string, unknown>>; total: number };
}

export function institutionReportExportUrl(
  institutionId: string,
  reportType: string,
  format: "csv" | "pdf"
) {
  const base = process.env.NEXT_PUBLIC_API_URL || "";
  return `${base}/institutions/${institutionId}/reports/export?report_type=${reportType}&export_format=${format}`;
}
