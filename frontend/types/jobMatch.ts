import type { InterviewQuestion } from "@/types/interview";

export type SkillMatchStatus = "matched" | "partial" | "not_evidenced";
export type RequirementType = "required" | "preferred";

export interface SkillAlignmentItem {
  skill: string;
  requirement_type: RequirementType;
  match_status: SkillMatchStatus;
  resume_evidence: string;
  gap_explanation: string;
}

export interface JobMatchScoreBreakdown {
  required_skill_count: number;
  required_matched: number;
  required_partial: number;
  required_not_evidenced: number;
  preferred_skill_count: number;
  preferred_matched: number;
  preferred_partial: number;
  preferred_not_evidenced: number;
  match_score: number;
  score_explanation: string;
  scoring_rules: string;
}

export interface JobMatchListItem {
  id: string;
  resume_id: string;
  job_title: string;
  match_score: number;
  status: "completed" | "failed";
  created_at: string;
}

export interface JobMatchResult {
  id: string;
  user_id: string;
  resume_id: string;
  job_title: string;
  status: "completed" | "failed";
  model: string;
  created_at: string;
  updated_at: string;
  job_description_excerpt: string;
  required_skills: string[];
  preferred_skills: string[];
  skill_alignments: SkillAlignmentItem[];
  score: JobMatchScoreBreakdown;
  gap_summary: string;
  strengths_for_role: string[];
  interview_questions: Omit<InterviewQuestion, "id">[];
  error_message?: string | null;
}

export interface CreateJobMatchPayload {
  resume_id: string;
  job_description: string;
  job_title?: string;
}
