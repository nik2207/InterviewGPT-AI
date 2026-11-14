import { apiClient } from "@/lib/api/client";
import type {
  GeneratePreparationPlanPayload,
  PreparationPlan,
  PreparationPlanListItem,
} from "@/types/preparationPlan";

export async function generatePreparationPlan(
  payload: GeneratePreparationPlanPayload
): Promise<PreparationPlan> {
  const { data } = await apiClient.post<PreparationPlan>("/preparation-plans", payload);
  return data;
}

export async function fetchPreparationPlans(): Promise<PreparationPlanListItem[]> {
  const { data } = await apiClient.get<{ plans: PreparationPlanListItem[] }>(
    "/preparation-plans"
  );
  return data.plans;
}

export async function fetchPreparationPlan(planId: string): Promise<PreparationPlan> {
  const { data } = await apiClient.get<PreparationPlan>(`/preparation-plans/${planId}`);
  return data;
}

export async function updatePlanTaskCompletion(
  planId: string,
  dayNumber: number,
  taskId: string,
  completed: boolean
): Promise<PreparationPlan> {
  const { data } = await apiClient.patch<PreparationPlan>(
    `/preparation-plans/${planId}/days/${dayNumber}/tasks/${taskId}`,
    { completed }
  );
  return data;
}

export async function regeneratePreparationPlan(planId: string): Promise<PreparationPlan> {
  const { data } = await apiClient.post<PreparationPlan>(
    `/preparation-plans/${planId}/regenerate`
  );
  return data;
}

export async function archivePreparationPlan(planId: string): Promise<PreparationPlan> {
  const { data } = await apiClient.post<PreparationPlan>(
    `/preparation-plans/${planId}/archive`
  );
  return data;
}
