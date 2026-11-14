"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import {
  buildSpeechMetrics,
  type InputMode,
  type SpeechMetrics,
} from "@/lib/speech/metrics";
import { metricsReportKey } from "@/lib/speech/metricsReport";
import {
  speechRecognitionHintMessage,
} from "@/lib/speech/locales";
import { useSpeechRecognition } from "@/lib/speech/useSpeechRecognition";
import type { InterviewLanguageCode } from "@/types/interview";

interface SpeechAnswerInputProps {
  value: string;
  onChange: (value: string) => void;
  onMetricsChange: (metrics: SpeechMetrics, inputMode: InputMode) => void;
  disabled?: boolean;
  answerLanguage?: InterviewLanguageCode;
  recognitionLocale?: string;
}

export function SpeechAnswerInput({
  value,
  onChange,
  onMetricsChange,
  disabled = false,
  answerLanguage = "en",
  recognitionLocale = "en-US",
}: SpeechAnswerInputProps) {
  const [inputMode, setInputMode] = useState<InputMode>("typed");
  const localeHint = speechRecognitionHintMessage(answerLanguage);
  const speech = useSpeechRecognition({
    recognitionLang: recognitionLocale,
    onTranscript: (text) => {
      setInputMode((prev) => (prev === "typed" ? "speech" : "mixed"));
      onChange(text);
    },
  });

  const metrics = useMemo(() => {
    const mode =
      inputMode === "typed" && speech.durationSeconds
        ? "mixed"
        : inputMode;
    return buildSpeechMetrics(value, mode, speech.durationSeconds);
  }, [value, inputMode, speech.durationSeconds]);

  const lastReportedKeyRef = useRef<string>("");

  useEffect(() => {
    const reportKey = metricsReportKey(metrics, metrics.input_mode);
    if (lastReportedKeyRef.current === reportKey) {
      return;
    }
    lastReportedKeyRef.current = reportKey;
    onMetricsChange(metrics, metrics.input_mode);
  }, [metrics, onMetricsChange]);

  return (
    <div className="space-y-3">
      {!speech.supported ? (
        <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          Speech recognition is not supported in this browser. Typed answers are
          fully supported.
        </p>
      ) : null}

      {localeHint ? (
        <p className="text-xs text-amber-900 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          {localeHint}
        </p>
      ) : null}

      {speech.permissionState === "denied" ? (
        <p className="text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          Microphone access was denied. Continue with typed answers.
        </p>
      ) : null}

      {speech.errorMessage ? (
        <p className="text-xs text-slate-600" role="status">{speech.errorMessage}</p>
      ) : null}

      <label className="block text-sm font-medium text-slate-700">
        Your answer
        <textarea
          className="mt-1 min-h-[140px] w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          value={value}
          onChange={(e) => {
            const next = e.target.value;
            if (speech.permissionState === "listening") {
              setInputMode("mixed");
            } else if (inputMode === "speech" && next !== value) {
              setInputMode("mixed");
            } else if (inputMode !== "speech") {
              setInputMode("typed");
            }
            onChange(next);
          }}
          disabled={disabled}
          placeholder="Type your answer here, or use speech input if available…"
        />
      </label>

      {speech.supported ? (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={disabled || speech.permissionState === "listening"}
            onClick={() => speech.start()}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-60"
          >
            {speech.permissionState === "listening"
              ? "Listening…"
              : "Start speech input"}
          </button>
          <button
            type="button"
            disabled={disabled || speech.permissionState !== "listening"}
            onClick={() => speech.stop()}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-60"
          >
            Stop speech input
          </button>
        </div>
      ) : null}

      <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
        <p className="font-medium text-slate-800">Answer metrics</p>
        <p className="mt-1">Input: {metrics.input_mode}</p>
        <p>Word count: {metrics.word_count ?? "—"}</p>
        {metrics.input_mode === "typed" ? (
          <p>Speaking duration / WPM: not measured (typed answer)</p>
        ) : (
          <>
            <p>
              Duration:{" "}
              {metrics.duration_seconds !== null
                ? `${metrics.duration_seconds}s`
                : "unavailable"}
            </p>
            <p>
              WPM:{" "}
              {metrics.words_per_minute !== null
                ? metrics.words_per_minute
                : "unavailable"}
            </p>
          </>
        )}
        <p>
          Filler words:{" "}
          {metrics.filler_word_count !== null ? metrics.filler_word_count : "—"}
        </p>
        <p className="mt-1 text-slate-500">{metrics.disclaimer}</p>
      </div>
    </div>
  );
}
