"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { SpeechAnswerInput } from "@/components/interviews/SpeechAnswerInput";
import {
  appendVoiceTranscript,
  requestVoiceClarification,
  updateVoiceSessionStatus,
} from "@/lib/api/voiceInterview";
import type { InputMode, SpeechMetrics } from "@/lib/speech/metrics";
import { useSpeechSynthesis } from "@/lib/speech/useSpeechSynthesis";
import { isSpeechRecognitionSupported } from "@/lib/speech/metrics";
import { SPEECH_BCP47, speechRecognitionHintMessage } from "@/lib/speech/locales";
import type {
  InterviewerTone,
  InterviewLanguageSettings,
  InterviewQuestion,
  VoiceInterviewState,
} from "@/types/interview";
import { DEFAULT_INTERVIEW_LANGUAGE } from "@/types/interview";

interface VoiceInterviewExperienceProps {
  sessionId: string;
  question: InterviewQuestion;
  voiceState: VoiceInterviewState;
  answerText: string;
  onAnswerChange: (value: string) => void;
  onMetricsChange: (metrics: SpeechMetrics, mode: InputMode) => void;
  onVoiceStateChange: (state: VoiceInterviewState) => void;
  submitting: boolean;
  onSubmit: () => void;
  clarificationBypass: boolean;
  onClarificationBypass: () => void;
  languageSettings?: InterviewLanguageSettings;
}

export function VoiceInterviewExperience({
  sessionId,
  question,
  voiceState,
  answerText,
  onAnswerChange,
  onMetricsChange,
  onVoiceStateChange,
  submitting,
  onSubmit,
  clarificationBypass,
  onClarificationBypass,
  languageSettings = DEFAULT_INTERVIEW_LANGUAGE,
}: VoiceInterviewExperienceProps) {
  const tone: InterviewerTone = voiceState.tone;
  const tts = useSpeechSynthesis();
  const questionLocale = SPEECH_BCP47[languageSettings.question_language];
  const answerLocale = SPEECH_BCP47[languageSettings.answer_language];
  const [muted, setMuted] = useState(false);
  const [clarificationNote, setClarificationNote] = useState<string | null>(null);
  const [checkingClarification, setCheckingClarification] = useState(false);
  const lastQuestionSpokenRef = useRef<string | null>(null);
  const recognitionSupported = isSpeechRecognitionSupported();

  const paused = voiceState.session_status === "paused";

  const speakQuestion = useCallback(async () => {
    if (muted || paused) {
      return;
    }
    const intro = `Question on ${question.category}.`;
    const line = `${intro} ${question.question}`;
    tts.speak(line, tone, questionLocale);
    try {
      const updated = await appendVoiceTranscript(sessionId, {
        role: "interviewer",
        text: line,
        question_id: question.id,
      });
      onVoiceStateChange(updated);
    } catch {
      /* non-blocking */
    }
  }, [
    muted,
    paused,
    question,
    questionLocale,
    sessionId,
    tone,
    tts,
    onVoiceStateChange,
  ]);

  useEffect(() => {
    if (lastQuestionSpokenRef.current === question.id) {
      return;
    }
    lastQuestionSpokenRef.current = question.id;
    setClarificationNote(null);
    onClarificationBypass();
    void speakQuestion();
  }, [question.id, speakQuestion, onClarificationBypass]);

  async function togglePause() {
    const next = paused ? "active" : "paused";
    if (next === "paused") {
      tts.cancel();
    }
    try {
      const updated = await updateVoiceSessionStatus(sessionId, next);
      onVoiceStateChange(updated);
    } catch {
      /* ignore */
    }
  }

  async function handleEndVoice() {
    tts.cancel();
    try {
      const updated = await updateVoiceSessionStatus(sessionId, "ended");
      onVoiceStateChange(updated);
    } catch {
      /* ignore */
    }
  }

  async function handleSubmitWithClarification(forceSubmit = false) {
    if (!answerText.trim()) {
      return;
    }
    setCheckingClarification(true);
    setClarificationNote(null);
    try {
      if (!forceSubmit && !clarificationBypass) {
        const result = await requestVoiceClarification(sessionId, {
          question_id: question.id,
          answer_draft: answerText,
        });
        if (result.needs_clarification && result.interviewer_message) {
          setClarificationNote(result.interviewer_message);
          if (!muted && !paused) {
            tts.speak(result.interviewer_message, tone, questionLocale);
          }
          const updatedVoice = {
            ...voiceState,
            transcript: [
              ...voiceState.transcript,
              {
                role: "interviewer" as const,
                text: result.interviewer_message,
                question_id: question.id,
                created_at: new Date().toISOString(),
              },
            ],
          };
          onVoiceStateChange(updatedVoice);
          return;
        }
      }
      await appendVoiceTranscript(sessionId, {
        role: "candidate",
        text: answerText.trim(),
        question_id: question.id,
      });
      onClarificationBypass();
      onSubmit();
    } catch {
      onSubmit();
    } finally {
      setCheckingClarification(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-control border border-app-border bg-app-surface p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-xs font-semibold uppercase text-app-muted">
              AI voice interviewer
            </p>
            <p className="text-sm text-app-ink capitalize">
              {tone} tone · {voiceState.session_status}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <SpeakingIndicator active={tts.speaking} listening={false} />
            <button
              type="button"
              className="btn-secondary text-xs"
              onClick={() => setMuted((v) => !v)}
            >
              {muted ? "Unmute interviewer" : "Mute interviewer"}
            </button>
            <button type="button" className="btn-secondary text-xs" onClick={togglePause}>
              {paused ? "Resume" : "Pause"}
            </button>
            <button type="button" className="btn-secondary text-xs" onClick={handleEndVoice}>
              End voice mode
            </button>
            <button
              type="button"
              className="btn-secondary text-xs"
              onClick={() => speakQuestion()}
              disabled={muted || paused}
            >
              Replay question
            </button>
          </div>
        </div>
        <p className="mt-2 text-xs text-app-muted">{voiceState.disclaimer}</p>
        {!tts.supported ? (
          <p className="mt-2 text-xs text-amber-800">
            Text-to-speech is not available in this browser. Read the question on screen.
          </p>
        ) : null}
        {!recognitionSupported ? (
          <p className="mt-2 text-xs text-amber-800">
            Speech recognition unsupported — use typed fallback below.
          </p>
        ) : null}
        {speechRecognitionHintMessage(languageSettings.answer_language) ? (
          <p className="mt-2 text-xs text-amber-800">
            {speechRecognitionHintMessage(languageSettings.answer_language)}
          </p>
        ) : null}
      </div>

      <section
        className="max-h-48 space-y-2 overflow-y-auto rounded-control border border-app-border bg-white p-3"
        aria-label="Interview conversation"
      >
        {voiceState.transcript.length === 0 ? (
          <p className="text-sm text-app-muted">Conversation transcript will appear here.</p>
        ) : (
          voiceState.transcript.map((entry, index) => (
            <div
              key={`${entry.created_at}-${index}`}
              className={`text-sm ${
                entry.role === "interviewer" ? "text-app-primary" : "text-app-ink"
              }`}
            >
              <span className="font-medium capitalize">{entry.role}: </span>
              {entry.language ? (
                <span className="mr-1 text-[10px] uppercase text-slate-400">
                  [{entry.language}]
                </span>
              ) : null}
              {entry.text}
            </div>
          ))
        )}
        {clarificationNote ? (
          <p className="text-sm font-medium text-amber-900">{clarificationNote}</p>
        ) : null}
      </section>

      <div className="rounded-control border border-dashed border-app-border bg-slate-50/80 p-3">
        <p className="text-xs font-medium text-app-muted">Live answer transcript</p>
        <p className="mt-1 min-h-[2rem] whitespace-pre-wrap text-sm text-app-ink">
          {answerText || "Speak or type your answer…"}
        </p>
      </div>

      <SpeechAnswerInput
        value={answerText}
        onChange={onAnswerChange}
        onMetricsChange={onMetricsChange}
        disabled={submitting || paused || voiceState.session_status === "ended"}
        answerLanguage={languageSettings.answer_language}
        recognitionLocale={answerLocale}
      />

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="btn-primary"
          disabled={
            submitting ||
            checkingClarification ||
            !answerText.trim() ||
            paused ||
            voiceState.session_status === "ended"
          }
          onClick={() => void handleSubmitWithClarification()}
        >
          {checkingClarification ? "Checking…" : "Submit answer"}
        </button>
        {clarificationNote ? (
          <button
            type="button"
            className="btn-secondary"
            onClick={() => {
              onClarificationBypass();
              void handleSubmitWithClarification(true);
            }}
          >
            Submit anyway
          </button>
        ) : null}
      </div>
    </div>
  );
}

function SpeakingIndicator({
  active,
  listening,
}: {
  active: boolean;
  listening: boolean;
}) {
  const on = active || listening;
  return (
    <div
      className="flex h-8 items-end gap-0.5 px-2"
      aria-label={on ? "Speaking indicator active" : "Speaking indicator idle"}
    >
      {[0, 1, 2, 3].map((bar) => (
        <span
          key={bar}
          className={`w-1 rounded-full bg-app-primary transition-all ${
            on ? "animate-pulse" : "opacity-30"
          }`}
          style={{ height: on ? `${8 + bar * 4}px` : "6px" }}
        />
      ))}
    </div>
  );
}
