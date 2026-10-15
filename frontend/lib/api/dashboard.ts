import type { DashboardStats, InterviewActivityItem } from "@/types/dashboard";

/**
 * Placeholder until backend dashboard/analytics endpoints exist.
 * Returns null metrics and an empty activity list — not fabricated stats.
 */
export async function fetchDashboardStats(): Promise<DashboardStats> {
  return {
    interviewsCompleted: null,
    practiceSessions: null,
    averageScore: null,
    preparationProgressPercent: null,
  };
}

export async function fetchRecentInterviewActivity(): Promise<
  InterviewActivityItem[]
> {
  return [];
}
