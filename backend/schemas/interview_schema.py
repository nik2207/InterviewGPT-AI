from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

DifficultyLevel = Literal["beginner", "intermediate", "advanced"]
InterviewType = Literal["technical", "behavioral", "mixed", "resume_based"]
InterviewerTone = Literal["friendly", "professional", "challenging"]
VoiceSessionStatus = Literal["active", "paused", "ended"]
VoiceTranscriptRole = Literal["interviewer", "candidate"]
SessionStatus = Literal["in_progress", "completed"]
EvaluationStatus = Literal["pending", "evaluated", "failed"]
InterviewLanguageCode = Literal["en", "hi", "mr"]

MULTILINGUAL_PRACTICE_DISCLAIMER = (
    "Multilingual practice uses AI for questions, feedback, and optional browser speech. "
    "Technical terms may stay in English. Browser speech recognition support varies by "
    "language and device — typed answers always work. Scores reflect relevance and technical "
    "content, not accent or language choice alone."
)


class InterviewLanguageSettings(BaseModel):
    question_language: InterviewLanguageCode = "en"
    answer_language: InterviewLanguageCode = "en"
    feedback_language: InterviewLanguageCode = "en"
    allow_bilingual_answers: bool = False
    practice_professional_english: bool = False

SCORING_DIMENSION_WEIGHTS: dict[str, float] = {
    "technical_correctness": 0.35,
    "relevance": 0.25,
    "completeness": 0.25,
    "answer_structure": 0.15,
}

SCORING_RULES_DESCRIPTION = (
    "Each dimension is scored 1–5 by the evaluator. "
    "Overall score (0–100) = sum((score/5) * weight) * 100 for dimensions: "
    "technical_correctness (35%), relevance (25%), completeness (25%), "
    "answer_structure (15%). Answer quality scoring uses typed answer text only."
)

INTERVIEW_LEVEL_SCORE_DESCRIPTION = (
    "Interview overall score = arithmetic mean of each evaluated answer's "
    "overall_score (0–100), computed at session completion."
)


class CustomInterviewQuestionInput(BaseModel):
    question: str = Field(..., min_length=5, max_length=500)
    category: str = Field(default="general", min_length=2, max_length=80)
    difficulty: DifficultyLevel = "intermediate"
    relevance: str = Field(default="General", min_length=2, max_length=300)
    evaluates: str = Field(default="Role fit", min_length=2, max_length=300)


VOICE_INTERVIEW_DISCLAIMER = (
    "Voice interview mode uses sequential browser text-to-speech and speech-to-text. "
    "It is not a full real-time duplex voice conversation. Raw audio is not stored."
)


class VoiceTranscriptEntry(BaseModel):
    role: VoiceTranscriptRole
    text: str = Field(..., min_length=1, max_length=8000)
    question_id: str | None = Field(default=None, max_length=64)
    created_at: datetime
    language: InterviewLanguageCode | None = None


class VoiceInterviewState(BaseModel):
    enabled: bool = False
    tone: InterviewerTone = "professional"
    session_status: VoiceSessionStatus = "active"
    transcript: list[VoiceTranscriptEntry] = Field(default_factory=list)
    disclaimer: str = VOICE_INTERVIEW_DISCLAIMER


class CreateInterviewSessionRequest(BaseModel):
    role: str = Field(..., min_length=2, max_length=120)
    difficulty: DifficultyLevel
    interview_type: InterviewType
    resume_id: str | None = Field(default=None, max_length=64)
    question_count: int = Field(default=5, ge=3, le=15)
    custom_questions: list[CustomInterviewQuestionInput] | None = None
    voice_interview_enabled: bool = False
    interviewer_tone: InterviewerTone = "professional"
    language: InterviewLanguageSettings = Field(
        default_factory=InterviewLanguageSettings
    )

    @field_validator("custom_questions")
    @classmethod
    def validate_custom_questions(
        cls, value: list[CustomInterviewQuestionInput] | None
    ) -> list[CustomInterviewQuestionInput] | None:
        if value is not None and len(value) < 1:
            raise ValueError("custom_questions must include at least one question")
        if value is not None and len(value) > 15:
            raise ValueError("custom_questions cannot exceed 15 items")
        return value


FollowUpType = Literal[
    "clarification",
    "technical_depth",
    "practical_scenario",
    "project_explanation",
    "behavioral_exploration",
]


class InterviewQuestionSnapshot(BaseModel):
    id: str
    question: str
    category: str
    difficulty: DifficultyLevel
    relevance: str
    evaluates: str
    is_follow_up: bool = False
    parent_question_id: str | None = None
    follow_up_type: FollowUpType | None = None
    skipped: bool = False


class GeminiFollowUpQuestionPayload(BaseModel):
    should_ask_follow_up: bool
    follow_up_type: FollowUpType | None = None
    question: str | None = Field(default=None, max_length=500)
    category: str | None = Field(default=None, max_length=80)
    difficulty: DifficultyLevel | None = None
    relevance: str | None = Field(default=None, max_length=300)
    evaluates: str | None = Field(default=None, max_length=300)
    rationale: str | None = Field(default=None, max_length=500)


class AnswerDimensionScores(BaseModel):
    technical_correctness: int = Field(..., ge=1, le=5)
    relevance: int = Field(..., ge=1, le=5)
    completeness: int = Field(..., ge=1, le=5)
    answer_structure: int = Field(..., ge=1, le=5)


StarElement = Literal["situation", "task", "action", "result"]


class StarImprovementAssessment(BaseModel):
    uses_star: bool
    missing_star_elements: list[StarElement] = Field(default_factory=list, max_length=4)
    specificity_suggestions: list[str] = Field(default_factory=list, max_length=6)


class GeminiAnswerImprovementCoach(BaseModel):
    missing_important_points: list[str] = Field(..., max_length=12)
    incorrect_or_unclear: list[str] = Field(default_factory=list, max_length=8)
    relevance_to_question: str = Field(..., min_length=10, max_length=1500)
    improved_example_answer: str = Field(..., min_length=20, max_length=4000)
    why_example_is_stronger: str = Field(..., min_length=10, max_length=2000)
    concepts_to_revise: list[str] = Field(default_factory=list, max_length=12)
    follow_up_practice_question: str = Field(..., min_length=10, max_length=500)
    action_to_take: str = Field(..., min_length=10, max_length=800)
    star_assessment: StarImprovementAssessment | None = None


class AnswerImprovementCoach(BaseModel):
    what_went_well: list[str] = Field(default_factory=list, max_length=8)
    missing_important_points: list[str] = Field(default_factory=list, max_length=12)
    incorrect_or_unclear: list[str] = Field(default_factory=list, max_length=8)
    relevance_to_question: str = Field(default="", max_length=1500)
    improved_example_answer: str = Field(default="", max_length=4000)
    why_example_is_stronger: str = Field(default="", max_length=2000)
    concepts_to_revise: list[str] = Field(default_factory=list, max_length=12)
    follow_up_practice_question: str = Field(default="", max_length=500)
    action_to_take: str = Field(default="", max_length=800)
    star_assessment: StarImprovementAssessment | None = None


class GeminiAnswerEvaluationPayload(BaseModel):
    dimension_scores: AnswerDimensionScores
    strengths: list[str] = Field(..., min_length=1, max_length=8)
    missing_concepts: list[str] = Field(..., max_length=10)
    improvement_suggestions: list[str] = Field(..., min_length=1, max_length=8)
    feedback_summary: str = Field(..., min_length=10, max_length=1500)
    language_fluency_feedback: str = Field(default="", max_length=1500)
    improvement_coach: GeminiAnswerImprovementCoach


class AnswerEvaluationResponse(BaseModel):
    dimension_scores: AnswerDimensionScores
    strengths: list[str]
    missing_concepts: list[str]
    improvement_suggestions: list[str]
    feedback_summary: str
    language_fluency_feedback: str = ""
    overall_score: float = Field(..., ge=0, le=100)
    scoring_rules: str = SCORING_RULES_DESCRIPTION
    improvement_coach: AnswerImprovementCoach | None = None


InputMode = Literal["typed", "speech", "mixed"]


class SpeechMetricsRecord(BaseModel):
    input_mode: InputMode
    word_count: int | None = None
    duration_seconds: float | None = None
    words_per_minute: float | None = None
    filler_word_count: int | None = None
    filler_words_used: list[str] = Field(default_factory=list, max_length=20)
    speech_timing_available: bool = False
    disclaimer: str = Field(
        default=(
            "Descriptive timing and word-use metrics only. "
            "Not a measure of confidence, personality, or psychological state."
        ),
        max_length=500,
    )


class SpeechMetricsInput(BaseModel):
    input_mode: InputMode = "typed"
    duration_seconds: float | None = Field(default=None, ge=0, le=3600)


class InterviewAnswerRecord(BaseModel):
    question_id: str
    submission_id: str
    answer_text: str
    submitted_at: datetime
    evaluation_status: EvaluationStatus
    evaluation: AnswerEvaluationResponse | None = None
    evaluated_at: datetime | None = None
    evaluation_error: str | None = None
    speech_metrics: SpeechMetricsRecord | None = None


class SubmitAnswerRequest(BaseModel):
    answer_text: str = Field(default="", max_length=8000)
    submission_id: str = Field(..., min_length=8, max_length=64)
    retry_evaluation: bool = False
    speech_metrics: SpeechMetricsInput | None = None


class InterviewSessionSummary(BaseModel):
    total_questions: int
    answered_questions: int
    average_score: float | None = None
    scoring_rules: str = SCORING_RULES_DESCRIPTION
    highlights: list[str] = Field(default_factory=list)
    focus_areas: list[str] = Field(default_factory=list)


class InterviewSessionResponse(BaseModel):
    id: str
    user_id: str
    role: str
    difficulty: DifficultyLevel
    interview_type: InterviewType
    resume_id: str | None
    status: SessionStatus
    questions: list[InterviewQuestionSnapshot]
    base_question_count: int | None = None
    follow_up_cap: int | None = None
    current_question_index: int
    answers: list[InterviewAnswerRecord]
    summary: InterviewSessionSummary | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    voice_interview: VoiceInterviewState | None = None
    language_settings: InterviewLanguageSettings = Field(
        default_factory=InterviewLanguageSettings
    )
    multilingual_disclaimer: str = MULTILINGUAL_PRACTICE_DISCLAIMER


class AppendVoiceTranscriptRequest(BaseModel):
    role: VoiceTranscriptRole
    text: str = Field(..., min_length=1, max_length=8000)
    question_id: str | None = Field(default=None, max_length=64)


class UpdateVoiceSessionStatusRequest(BaseModel):
    session_status: VoiceSessionStatus


class VoiceClarificationRequest(BaseModel):
    question_id: str = Field(..., min_length=1, max_length=64)
    answer_draft: str = Field(..., max_length=8000)


class GeminiVoiceClarificationPayload(BaseModel):
    needs_clarification: bool
    interviewer_message: str | None = Field(default=None, max_length=1500)


class VoiceClarificationResponse(BaseModel):
    needs_clarification: bool
    interviewer_message: str | None = None
    disclaimer: str = (
        "Clarification prompts do not include scoring or model answers."
    )


class InterviewSessionListResponse(BaseModel):
    sessions: list[InterviewSessionResponse]


class InterviewHistoryItem(BaseModel):
    id: str
    role: str
    difficulty: DifficultyLevel
    interview_type: InterviewType
    completed_at: datetime
    question_count: int
    overall_score: float | None = None
    score_description: str = INTERVIEW_LEVEL_SCORE_DESCRIPTION


class InterviewHistoryListResponse(BaseModel):
    interviews: list[InterviewHistoryItem]


TRANSCRIPT_AUDIO_RETENTION_POLICY = (
    "InterviewGPT does not store raw audio from mock interviews. Voice mode saves "
    "text transcripts only. Deleting an interview removes answers, evaluations, "
    "voice transcripts, and practice drafts for that session."
)

TRANSCRIPT_TEXT_DISCLAIMER = (
    "Transcript replay is reconstructed from submitted answers and optional voice "
    "transcript text. No audio playback is available unless a recording URL is "
    "explicitly stored for your account."
)


class TranscriptTiming(BaseModel):
    submitted_at: datetime | None = None
    duration_seconds: float | None = None
    words_per_minute: float | None = None
    timing_reliable: bool = False


class PracticeRevisionSnapshot(BaseModel):
    question_id: str
    draft_text: str
    updated_at: datetime


class TranscriptReviewItem(BaseModel):
    sequence: int = Field(..., ge=1)
    question: InterviewQuestionSnapshot
    answer: InterviewAnswerRecord | None = None
    answer_status: Literal["answered", "skipped", "unanswered", "pending", "failed"]
    is_weak: bool = False
    is_bookmarked: bool = False
    timing: TranscriptTiming | None = None
    voice_transcript: list[VoiceTranscriptEntry] = Field(default_factory=list)
    audio_recording_available: bool = False
    practice_revision: PracticeRevisionSnapshot | None = None


class InterviewTranscriptReviewResponse(BaseModel):
    session_id: str
    role: str
    status: SessionStatus
    completed_at: datetime | None = None
    bookmarks: list[str] = Field(default_factory=list)
    items: list[TranscriptReviewItem]
    voice_disclaimer: str = VOICE_INTERVIEW_DISCLAIMER
    audio_playback_supported: bool = False
    audio_retention_policy: str = TRANSCRIPT_AUDIO_RETENTION_POLICY
    text_transcript_disclaimer: str = TRANSCRIPT_TEXT_DISCLAIMER
    language_settings: InterviewLanguageSettings = Field(
        default_factory=InterviewLanguageSettings
    )
    multilingual_disclaimer: str = MULTILINGUAL_PRACTICE_DISCLAIMER


class UpdateTranscriptBookmarksRequest(BaseModel):
    question_ids: list[str] = Field(default_factory=list, max_length=30)


class UpdatePracticeRevisionRequest(BaseModel):
    draft_text: str = Field(..., max_length=8000)


def compute_overall_score(scores: AnswerDimensionScores) -> float:
    total = 0.0
    for dimension, weight in SCORING_DIMENSION_WEIGHTS.items():
        value = getattr(scores, dimension)
        total += (value / 5.0) * weight
    return round(total * 100.0, 1)
