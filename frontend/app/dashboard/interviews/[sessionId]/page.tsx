"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import Link from "next/link";

import { InterviewLanguageIndicators } from "@/components/interviews/InterviewLanguageIndicators";
import { InterviewCoachingPanel } from "@/components/interviews/InterviewCoachingPanel";
import { InterviewFeedback } from "@/components/interviews/InterviewFeedback";
import { InterviewSummary } from "@/components/interviews/InterviewSummary";
import { SpeechAnswerInput } from "@/components/interviews/SpeechAnswerInput";
import { VoiceInterviewExperience } from "@/components/interviews/VoiceInterviewExperience";
import type { InputMode, SpeechMetrics } from "@/lib/speech/metrics";
import {
  completeInterviewSession,
  fetchInterviewSession,
  skipFollowUpQuestion,
  submitInterviewAnswer,
} from "@/lib/api/interviews";
import type { FollowUpType } from "@/types/interview";
import { SPEECH_BCP47 } from "@/lib/speech/locales";
import {
  DEFAULT_INTERVIEW_LANGUAGE,
  type InterviewAnswer,
  type InterviewSession,
  type VoiceInterviewState,
} from "@/types/interview";

function getErrorMessage(error: unknown): string {
  if (
    typeof error === "object" &&
    error !== null &&
    "response" in error &&
    typeof (error as { response?: { data?: { detail?: string } } }).response
      ?.data?.detail === "string"
  ) {
    return (error as { response: { data: { detail: string } } }).response.data
      .detail;
  }
  return "Something went wrong. Please try again.";
}

const FOLLOW_UP_LABELS: Record<FollowUpType, string> = {
  clarification: "Clarification",
  technical_depth: "Technical depth",
  practical_scenario: "Practical scenario",
  project_explanation: "Project explanation",
  behavioral_exploration: "Behavioural exploration",
};

function newSubmissionId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID().replace(/-/g, "");
  }
  return `sub-${Date.now()}`;
}

export default function InterviewRoomPage() {
  const params = useParams<{ sessionId: string }>();
  const sessionId = params.sessionId;

  const [session, setSession] = useState<InterviewSession | null>(null);
  const [answerText, setAnswerText] = useState("");
  const [submissionId, setSubmissionId] = useState(() => newSubmissionId());
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submissionSlow, setSubmissionSlow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastFeedback, setLastFeedback] = useState<InterviewAnswer | null>(null);
  const [speechPayload, setSpeechPayload] = useState<{
    input_mode: InputMode;
    duration_seconds: number | null;
  }>({ input_mode: "typed", duration_seconds: null });
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [mobileCoachOpen, setMobileCoachOpen] = useState(false);
  const [practiceMode, setPracticeMode] = useState(false);
  const [practicePrompt, setPracticePrompt] = useState<string | null>(null);
  useEffect(() => {
    if (!submitting) {
      setSubmissionSlow(false);
      return;
    }
    const timer = window.setTimeout(() => setSubmissionSlow(true), 3000);
    return () => window.clearTimeout(timer);
  }, [submitting]);
  const [voiceInterview, setVoiceInterview] = useState<VoiceInterviewState | null>(
    null
  );
  const [clarificationBypass, setClarificationBypass] = useState(false);

  const handleSpeechMetricsChange = useCallback(
    (metrics: SpeechMetrics, mode: InputMode) => {
      setSpeechPayload((prev) => {
        const next = {
          input_mode: mode,
          duration_seconds: metrics.duration_seconds,
        };
        if (
          prev.input_mode === next.input_mode &&
          prev.duration_seconds === next.duration_seconds
        ) {
          return prev;
        }
        return next;
      });
    },
    []
  );

  const loadSession = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchInterviewSession(sessionId);
      setSession(data);
      setVoiceInterview(data.voice_interview ?? null);
    } catch (loadError) {
      setError(getErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    loadSession();
  }, [loadSession]);

  useEffect(() => {
    if (!session || session.status !== "in_progress") {
      return;
    }
    if (voiceInterview?.session_status === "paused") {
      return;
    }
    const started = window.setInterval(() => {
      setElapsedSeconds((value) => value + 1);
    }, 1000);
    return () => window.clearInterval(started);
  }, [session?.id, session?.status, voiceInterview?.session_status]);

  const currentQuestion = useMemo(() => {
    if (!session) {
      return null;
    }
    const index = session.current_question_index;
    return session.questions[index] ?? null;
  }, [session]);

  const progressLabel = useMemo(() => {
    if (!session) {
      return "";
    }
    const answered = session.answers.filter(
      (a) => a.evaluation_status === "evaluated"
    ).length;
    const base = session.base_question_count ?? session.questions.length;
    const followUps = session.questions.filter((q) => q.is_follow_up).length;
    const position = Math.min(session.current_question_index + 1, session.questions.length);
    const mainLabel =
      followUps > 0
        ? `${position} of ${session.questions.length} (${base} main + ${followUps} follow-up${followUps === 1 ? "" : "s"})`
        : `${position} of ${session.questions.length}`;
    return `Question ${mainLabel}`;
  }, [session]);

  const startPracticeImprovement = useCallback(() => {
    const coach = lastFeedback?.evaluation?.improvement_coach;
    const prompt =
      coach?.follow_up_practice_question ||
      "Rewrite your answer using the suggested structure in the coach panel.";
    setPracticePrompt(prompt);
    setPracticeMode(true);
    setAnswerText("");
    setSpeechPayload({ input_mode: "typed", duration_seconds: null });
  }, [lastFeedback]);

  async function handleSubmit(retryEvaluation = false) {
    if (!session) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const updated = await submitInterviewAnswer(sessionId, {
        submission_id: submissionId,
        answer_text: answerText,
        retry_evaluation: retryEvaluation,
        speech_metrics: retryEvaluation ? undefined : speechPayload,
      });
      setSession(updated);
      setVoiceInterview(updated.voice_interview ?? voiceInterview);
      setClarificationBypass(false);
      const currentQ = updated.questions[updated.current_question_index - 1];
      const latestAnswer = updated.answers
        .filter((a) => a.question_id === (currentQ?.id ?? ""))
        .at(-1);
      if (latestAnswer?.evaluation_status === "evaluated" && latestAnswer.evaluation) {
        setLastFeedback(latestAnswer);
        setAnswerText("");
        setSubmissionId(newSubmissionId());
        setSpeechPayload({ input_mode: "typed", duration_seconds: null });
      } else if (latestAnswer?.evaluation_status === "failed") {
        setLastFeedback(latestAnswer);
        setError(
          latestAnswer.evaluation_error ??
            "Evaluation failed. Your answer was saved — retry evaluation."
        );
      }
    } catch (submitError) {
      setError(getErrorMessage(submitError));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSkipFollowUp() {
    if (!session || !currentQuestion?.is_follow_up) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const updated = await skipFollowUpQuestion(sessionId, currentQuestion.id);
      setSession(updated);
      setVoiceInterview(updated.voice_interview ?? voiceInterview);
      setAnswerText("");
      setSubmissionId(newSubmissionId());
      setSpeechPayload({ input_mode: "typed", duration_seconds: null });
    } catch (skipError) {
      setError(getErrorMessage(skipError));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleComplete() {
    setSubmitting(true);
    setError(null);
    try {
      const completed = await completeInterviewSession(sessionId);
      setSession(completed);
      setVoiceInterview(completed.voice_interview ?? null);
    } catch (completeError) {
      setError(getErrorMessage(completeError));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <p className="text-sm text-slate-500" aria-live="polite">
        Loading interview…
      </p>
    );
  }

  if (!session) {
    return (
      <p className="text-sm text-red-600" role="alert">
        {error ?? "Interview not found."}
      </p>
    );
  }

  if (session.status === "completed") {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <InterviewSummary session={session} />
        <Link
          href={`/dashboard/interviews/history/${session.id}/review`}
          className="inline-block text-sm font-medium text-brand-700 hover:underline"
        >
          View in interview history &amp; download report
        </Link>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-card">
          <h2 className="text-sm font-semibold text-slate-900">Answer review</h2>
          <ul className="mt-3 space-y-4">
            {session.answers.map((answer) => {
              const question = session.questions.find(
                (q) => q.id === answer.question_id
              );
              return (
                <li key={answer.submission_id} className="border-t border-slate-100 pt-3">
                  <p className="text-sm font-medium text-slate-800">
                    {question?.question ?? "Question"}
                  </p>
                  <p className="mt-1 text-sm text-slate-600">{answer.answer_text}</p>
                  {answer.evaluation ? (
                    <div className="mt-2">
                      <InterviewFeedback
                        evaluation={answer.evaluation}
                        originalAnswer={answer.answer_text}
                      />
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    );
  }

  const allAnswered =
    session.current_question_index >= session.questions.length &&
    session.answers.every((a) => a.evaluation_status === "evaluated");

  const minutes = Math.floor(elapsedSeconds / 60);
  const seconds = elapsedSeconds % 60;
  const elapsedLabel = `${minutes}:${seconds.toString().padStart(2, "0")}`;

  const feedbackForPanel =
    lastFeedback &&
    (lastFeedback.question_id === currentQuestion?.id ||
      (currentQuestion?.is_follow_up &&
        lastFeedback.question_id === currentQuestion.parent_question_id))
      ? lastFeedback
      : null;

  return (
    <div className="mx-auto max-w-7xl space-y-4">
      <header className="app-card flex flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-5">
        <div className="flex items-center gap-3">
          <Link href="/dashboard/interviews" className="text-sm text-app-muted hover:text-app-primary">
            ← Back
          </Link>
          <div>
            <h1 className="text-lg font-semibold text-app-ink">{session.role}</h1>
            <p className="text-xs text-app-muted capitalize">
              {session.difficulty} · {session.interview_type.replace("_", " ")} ·{" "}
              {progressLabel}
            </p>
            <InterviewLanguageIndicators
              settings={session.language_settings ?? DEFAULT_INTERVIEW_LANGUAGE}
              compact
            />
          </div>
        </div>
        <div className="flex items-center gap-3 text-sm text-app-muted">
          <span aria-label="Elapsed time">⏱ {elapsedLabel}</span>
          <button
            type="button"
            className="btn-secondary lg:hidden"
            onClick={() => setMobileCoachOpen((v) => !v)}
          >
            {mobileCoachOpen ? "Hide coaching" : "Coaching"}
          </button>
        </div>
      </header>

      {error ? (
        <p className="rounded-control border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}

      {session.multilingual_disclaimer ? (
        <p className="rounded-control border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
          {session.multilingual_disclaimer}
        </p>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          {currentQuestion ? (
            <div className="app-card p-6">
              <div className="flex flex-wrap items-center gap-2 text-xs font-medium uppercase tracking-wide text-app-primary">
                {currentQuestion.is_follow_up ? (
                  <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-900">
                    Follow-up
                    {currentQuestion.follow_up_type
                      ? ` · ${FOLLOW_UP_LABELS[currentQuestion.follow_up_type]}`
                      : ""}
                  </span>
                ) : (
                  <span>Main question</span>
                )}
                <span>{currentQuestion.category}</span>
                <span className="rounded-full bg-app-primary-soft px-2 py-0.5 text-app-primary">
                  {currentQuestion.difficulty}
                </span>
              </div>
              <h2 className="mt-3 text-xl font-medium leading-relaxed text-app-ink">
                {currentQuestion.question}
              </h2>

              {practiceMode && practicePrompt ? (
                <div className="mt-4 rounded-control border border-app-primary/30 bg-app-primary-soft/40 p-3 text-sm text-app-ink">
                  <p className="font-medium">Practice mode</p>
                  <p className="mt-1 text-app-muted">{practicePrompt}</p>
                  <p className="mt-2 text-xs text-app-muted">
                    Draft an improved answer below. Submit when ready — this counts as
                    your official response for this question if you have not advanced yet.
                  </p>
                  <button
                    type="button"
                    className="mt-2 text-xs font-medium text-app-primary hover:underline"
                    onClick={() => setPracticeMode(false)}
                  >
                    Exit practice mode
                  </button>
                </div>
              ) : null}

              <div className="mt-6">
                {voiceInterview?.enabled &&
                voiceInterview.session_status !== "ended" ? (
                  <VoiceInterviewExperience
                    sessionId={sessionId}
                    question={currentQuestion}
                    voiceState={voiceInterview}
                    answerText={answerText}
                    onAnswerChange={setAnswerText}
                    onMetricsChange={handleSpeechMetricsChange}
                    onVoiceStateChange={setVoiceInterview}
                    submitting={submitting}
                    onSubmit={() => handleSubmit(false)}
                    clarificationBypass={clarificationBypass}
                    onClarificationBypass={() => setClarificationBypass(true)}
                    languageSettings={
                      session.language_settings ?? DEFAULT_INTERVIEW_LANGUAGE
                    }
                  />
                ) : (
                  <>
                    <SpeechAnswerInput
                      value={answerText}
                      onChange={setAnswerText}
                      disabled={submitting}
                      onMetricsChange={handleSpeechMetricsChange}
                      answerLanguage={
                        (session.language_settings ?? DEFAULT_INTERVIEW_LANGUAGE)
                          .answer_language
                      }
                      recognitionLocale={
                        SPEECH_BCP47[
                          (session.language_settings ?? DEFAULT_INTERVIEW_LANGUAGE)
                            .answer_language
                        ]
                      }
                    />
                    <div className="mt-4 flex flex-wrap gap-2">
                      {currentQuestion.is_follow_up ? (
                        <button
                          type="button"
                          disabled={submitting}
                          onClick={() => handleSkipFollowUp()}
                          className="btn-secondary"
                        >
                          Skip follow-up
                        </button>
                      ) : null}
                      <button
                        type="button"
                        disabled={submitting || !answerText.trim()}
                        onClick={() => handleSubmit(false)}
                        className="btn-primary"
                      >
                        {submitting
                          ? submissionSlow
                            ? "Generating feedback…"
                            : "Submitting…"
                          : "Submit answer"}
                      </button>
                      {lastFeedback?.evaluation_status === "failed" &&
                      lastFeedback.question_id === currentQuestion.id ? (
                        <button
                          type="button"
                          disabled={submitting}
                          onClick={() => handleSubmit(true)}
                          className="btn-secondary"
                        >
                          Retry evaluation
                        </button>
                      ) : null}
                    </div>
                  </>
                )}
              </div>

              {currentQuestion.is_follow_up ? (
                <div className="mt-4">
                  <button
                    type="button"
                    disabled={submitting}
                    onClick={() => handleSkipFollowUp()}
                    className="btn-secondary"
                  >
                    Skip follow-up
                  </button>
                </div>
              ) : null}

              {voiceInterview?.enabled &&
              lastFeedback?.evaluation_status === "failed" &&
              lastFeedback.question_id === currentQuestion.id ? (
                <div className="mt-4">
                  <button
                    type="button"
                    disabled={submitting}
                    onClick={() => handleSubmit(true)}
                    className="btn-secondary"
                  >
                    Retry evaluation
                  </button>
                </div>
              ) : null}
            </div>
          ) : null}

          {allAnswered ? (
            <button
              type="button"
              disabled={submitting}
              onClick={handleComplete}
              className="btn-primary bg-emerald-600 hover:bg-emerald-700"
            >
              Finish interview
            </button>
          ) : null}
        </div>

        <div className={`${mobileCoachOpen ? "block" : "hidden"} lg:block`}>
          <InterviewCoachingPanel
            question={currentQuestion}
            lastFeedback={feedbackForPanel}
            submitting={submitting}
            onPracticeImprovement={startPracticeImprovement}
          />
        </div>
      </div>
    </div>
  );
}
