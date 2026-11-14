export type ReadinessStatus = "available" | "insufficient_data";

export interface DataCoverageItem {
  source: string;
  available: boolean;
  detail: string;
  last_updated: string | null;
}

export interface OverallReadiness {
  score: number | null;
  status: ReadinessStatus;
  message: string;
}

export interface ComponentScore {
  score: number | null;
  status: ReadinessStatus;
  detail: string;
  sample_size: number;
}

export interface InterviewTrendPoint {
  session_id: string;
  role: string;
  completed_at: string;
  overall_score: number | null;
}

export interface PreparationPlanSummary {
  plan_id: string;
  status: string;
  progress_percent: number;
  tasks_completed: number;
  tasks_total: number;
  last_updated: string;
}

export interface CommunicationIndicators {
  status: ReadinessStatus;
  speech_answer_count: number;
  average_words_per_minute?: number | null;
  average_filler_words?: number | null;
  disclaimer: string;
  detail: string;
}

export interface CareerReadinessReport {
  id: string;
  user_id: string;
  resume_id: string;
  job_match_id: string | null;
  target_role: string;
  generated_at: string;
  data_coverage: {
    items: DataCoverageItem[];
    summary: string;
  };
  overall_readiness: OverallReadiness;
  resume_job_alignment: ComponentScore;
  technical_knowledge: ComponentScore;
  answer_relevance: ComponentScore;
  answer_completeness: ComponentScore;
  answer_structure: ComponentScore;
  communication_indicators: CommunicationIndicators;
  strongest_skills: string[];
  skills_requiring_improvement: string[];
  interview_performance_trends: InterviewTrendPoint[];
  preparation_plan: PreparationPlanSummary | null;
  recommended_next_actions: string[];
  scoring_rules: string;
}

export interface CareerReadinessListItem {
  id: string;
  resume_id: string;
  job_match_id: string | null;
  target_role: string;
  overall_score: number | null;
  overall_status: ReadinessStatus;
  generated_at: string;
}
