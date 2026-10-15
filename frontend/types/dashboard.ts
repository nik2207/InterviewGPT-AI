/** Dashboard metrics — populated when backend analytics endpoints exist. */
export interface DashboardStats {
  interviewsCompleted: number | null;
  practiceSessions: number | null;
  averageScore: number | null;
  preparationProgressPercent: number | null;
}

export interface InterviewActivityItem {
  id: string;
  title: string;
  completedAt: string;
  score: number | null;
}
