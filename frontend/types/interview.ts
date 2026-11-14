export type InterviewLanguageCode = "en" | "hi" | "mr";

export interface InterviewLanguageSettings {
  question_language: InterviewLanguageCode;
  answer_language: InterviewLanguageCode;
  feedback_language: InterviewLanguageCode;
  allow_bilingual_answers: boolean;
  practice_professional_english: boolean;
}

export type DifficultyLevel = "beginner" | "intermediate" | "advanced";
export type InterviewType = "technical" | "behavioral" | "mixed" | "resume_based";
export type InterviewerTone = "friendly" | "professional" | "challenging";
export type VoiceSessionStatus = "active" | "paused" | "ended";
export type VoiceTranscriptRole = "interviewer" | "candidate";

export interface VoiceTranscriptEntry {
  role: VoiceTranscriptRole;
  text: string;
  question_id: string | null;
  created_at: string;
  language?: InterviewLanguageCode | null;
}

export interface VoiceInterviewState {
  enabled: boolean;
  tone: InterviewerTone;
  session_status: VoiceSessionStatus;
  transcript: VoiceTranscriptEntry[];
  disclaimer: string;
}

export interface VoiceClarificationResult {
  needs_clarification: boolean;
  interviewer_message: string | null;
  disclaimer: string;
}
export type SessionStatus = "in_progress" | "completed";
export type EvaluationStatus = "pending" | "evaluated" | "failed";

export type FollowUpType =
  | "clarification"
  | "technical_depth"
  | "practical_scenario"
  | "project_explanation"
  | "behavioral_exploration";

export interface InterviewQuestion {
  id: string;
  question: string;
  category: string;
  difficulty: DifficultyLevel;
  relevance: string;
  evaluates: string;
  is_follow_up?: boolean;
  parent_question_id?: string | null;
  follow_up_type?: FollowUpType | null;
  skipped?: boolean;
}

export interface AnswerDimensionScores {
  technical_correctness: number;
  relevance: number;
  completeness: number;
  answer_structure: number;
}

export type StarElement = "situation" | "task" | "action" | "result";

export interface StarImprovementAssessment {
  uses_star: boolean;
  missing_star_elements: StarElement[];
  specificity_suggestions: string[];
}

export interface AnswerImprovementCoach {
  what_went_well: string[];
  missing_important_points: string[];
  incorrect_or_unclear: string[];
  relevance_to_question: string;
  improved_example_answer: string;
  why_example_is_stronger: string;
  concepts_to_revise: string[];
  follow_up_practice_question: string;
  action_to_take: string;
  star_assessment?: StarImprovementAssessment | null;
}

export interface AnswerEvaluation {
  dimension_scores: AnswerDimensionScores;
  strengths: string[];
  missing_concepts: string[];
  improvement_suggestions: string[];
  feedback_summary: string;
  language_fluency_feedback?: string;
  overall_score: number;
  scoring_rules: string;
  improvement_coach?: AnswerImprovementCoach | null;
}

export type InputMode = "typed" | "speech" | "mixed";

export interface SpeechMetrics {
  input_mode: InputMode;
  word_count: number | null;
  duration_seconds: number | null;
  words_per_minute: number | null;
  filler_word_count: number | null;
  filler_words_used: string[];
  speech_timing_available: boolean;
  disclaimer: string;
}

export interface InterviewAnswer {
  question_id: string;
  submission_id: string;
  answer_text: string;
  submitted_at: string;
  evaluation_status: EvaluationStatus;
  evaluation: AnswerEvaluation | null;
  evaluated_at: string | null;
  evaluation_error?: string | null;
  speech_metrics?: SpeechMetrics | null;
}

export interface InterviewHistoryItem {
  id: string;
  role: string;
  difficulty: DifficultyLevel;
  interview_type: InterviewType;
  completed_at: string;
  question_count: number;
  overall_score: number | null;
  score_description: string;
}

export interface InterviewSummary {
  total_questions: number;
  answered_questions: number;
  average_score: number | null;
  scoring_rules: string;
  highlights: string[];
  focus_areas: string[];
}

export interface InterviewSession {
  id: string;
  user_id: string;
  role: string;
  difficulty: DifficultyLevel;
  interview_type: InterviewType;
  resume_id: string | null;
  status: SessionStatus;
  questions: InterviewQuestion[];
  base_question_count?: number | null;
  follow_up_cap?: number | null;
  current_question_index: number;
  answers: InterviewAnswer[];
  summary: InterviewSummary | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  voice_interview?: VoiceInterviewState | null;
  language_settings?: InterviewLanguageSettings;
  multilingual_disclaimer?: string;
}

export const DEFAULT_INTERVIEW_LANGUAGE: InterviewLanguageSettings = {
  question_language: "en",
  answer_language: "en",
  feedback_language: "en",
  allow_bilingual_answers: false,
  practice_professional_english: false,
};

export interface CreateInterviewPayload {
  role: string;
  difficulty: DifficultyLevel;
  interview_type: InterviewType;
  resume_id?: string;
  question_count?: number;
  voice_interview_enabled?: boolean;
  interviewer_tone?: InterviewerTone;
  language?: InterviewLanguageSettings;
}
