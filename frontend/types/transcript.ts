import type {
  FollowUpType,
  InterviewAnswer,
  InterviewLanguageSettings,
  InterviewQuestion,
  SessionStatus,
  VoiceTranscriptEntry,
} from "@/types/interview";

export interface TranscriptTiming {
  submitted_at: string | null;
  duration_seconds: number | null;
  words_per_minute: number | null;
  timing_reliable: boolean;
}

export interface PracticeRevisionSnapshot {
  question_id: string;
  draft_text: string;
  updated_at: string;
}

export type TranscriptAnswerStatus =
  | "answered"
  | "skipped"
  | "unanswered"
  | "pending"
  | "failed";

export interface TranscriptReviewItem {
  sequence: number;
  question: InterviewQuestion;
  answer: InterviewAnswer | null;
  answer_status: TranscriptAnswerStatus;
  is_weak: boolean;
  is_bookmarked: boolean;
  timing: TranscriptTiming | null;
  voice_transcript: VoiceTranscriptEntry[];
  audio_recording_available: boolean;
  practice_revision: PracticeRevisionSnapshot | null;
}

export interface InterviewTranscriptReview {
  session_id: string;
  role: string;
  status: SessionStatus;
  completed_at: string | null;
  bookmarks: string[];
  items: TranscriptReviewItem[];
  voice_disclaimer: string;
  audio_playback_supported: boolean;
  audio_retention_policy: string;
  text_transcript_disclaimer: string;
  language_settings?: InterviewLanguageSettings;
  multilingual_disclaimer?: string;
}

export type TranscriptFilter = "all" | "weak" | "bookmarked" | "main" | "follow_up";

export const FOLLOW_UP_TYPE_LABELS: Record<FollowUpType, string> = {
  clarification: "Clarification",
  technical_depth: "Technical depth",
  practical_scenario: "Practical scenario",
  project_explanation: "Project explanation",
  behavioral_exploration: "Behavioural exploration",
};
