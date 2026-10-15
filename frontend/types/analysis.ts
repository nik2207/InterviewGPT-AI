export type DifficultyLevel = "beginner" | "intermediate" | "advanced";

export interface InterviewQuestion {
  question: string;
  category: string;
  difficulty: DifficultyLevel;
  relevance: string;
  evaluates: string;
}

export interface ResumeAnalysisSections {
  professional_summary: string;
  skills: string[];
  experience_analysis: string;
  projects_analysis: string;
  strengths: string[];
  areas_to_improve: string[];
  missing_or_unclear_information: string[];
  ats_readability_suggestions: string[];
  role_recommendations: string[];
  skill_gaps: string[];
}

export interface ResumeAnalysisResult {
  id: string;
  resume_id: string;
  user_id: string;
  status: "completed" | "failed";
  model: string;
  created_at: string;
  updated_at: string;
  analysis: ResumeAnalysisSections;
  interview_questions: InterviewQuestion[];
  cached?: boolean;
}
