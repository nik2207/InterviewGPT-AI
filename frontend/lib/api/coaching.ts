import { apiClient } from "@/lib/api/client";

export interface CoachingPlanPayload {
  observed_strengths: string[];
  observed_gaps: string[];
  recommended_focus_areas: string[];
  practice_suggestions: string[];
  summary: string;
}

export interface CoachingPlanResponse {
  session_id: string;
  status:
    | "insufficient_data"
    | "completed"
    | "generation_failed"
    | "validation_failed";
  generated_at: string;
  evidence_count: number;
  plan: CoachingPlanPayload | null;
  message: string | null;
  disclaimer: string;
}

export async function fetchCoachingPlan(
  sessionId: string
): Promise<CoachingPlanResponse> {
  const { data } = await apiClient.get<CoachingPlanResponse>(
    `/interviews/${sessionId}/coaching-plan`
  );
  return data;
}
