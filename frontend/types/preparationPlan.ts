export type PlanStatus = "active" | "archived";
export type PlanTaskType = "learning" | "practice_question" | "exercise" | "review";

export interface PreparationPlanTask {
  task_id: string;
  title: string;
  description: string;
  task_type: PlanTaskType;
  estimated_minutes: number;
  completed: boolean;
  completed_at: string | null;
}

export interface PreparationPlanDay {
  day_number: number;
  relative_label: string;
  scheduled_date: string;
  theme: string;
  learning_objective: string;
  skills_to_practice: string[];
  learning_activities: string[];
  interview_questions: string[];
  practical_exercise: string | null;
  estimated_duration_minutes: number;
  completion_criteria: string;
  tasks: PreparationPlanTask[];
  day_completed: boolean;
}

export interface PreparationPlanListItem {
  id: string;
  resume_id: string;
  job_match_id: string | null;
  status: PlanStatus;
  daily_study_minutes: number;
  progress_percent: number;
  created_at: string;
  plan_start_date: string;
}

export interface PreparationPlan {
  id: string;
  user_id: string;
  resume_id: string;
  job_match_id: string | null;
  status: PlanStatus;
  daily_study_minutes: number;
  model: string;
  plan_start_date: string;
  created_at: string;
  updated_at: string;
  plan_summary: string;
  priority_gaps: string[];
  days: PreparationPlanDay[];
  progress_percent: number;
  tasks_completed: number;
  tasks_total: number;
  today_day_number: number | null;
}

export interface GeneratePreparationPlanPayload {
  resume_id: string;
  job_match_id?: string;
  daily_study_minutes: number;
  archive_plan_id?: string;
}
