export const FILLER_WORDS = [
  "um",
  "uh",
  "like",
  "actually",
  "basically",
  "literally",
  "sort of",
  "kind of",
  "you know",
] as const;

export const SPEECH_METRICS_DISCLAIMER =
  "Descriptive timing and word-use metrics only. Not a measure of confidence, personality, or psychological state.";

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

export function countWords(text: string): number {
  const cleaned = text.trim();
  if (!cleaned) {
    return 0;
  }
  return cleaned.match(/\b[\w']+\b/gu)?.length ?? 0;
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function countFillerWords(text: string): {
  count: number;
  used: string[];
} {
  const cleaned = text.trim();
  if (!cleaned) {
    return { count: 0, used: [] };
  }
  let total = 0;
  const used: string[] = [];
  for (const phrase of FILLER_WORDS) {
    const pattern = phrase.includes(" ")
      ? new RegExp(`(?<!\\w)${escapeRegex(phrase)}(?!\\w)`, "gi")
      : new RegExp(`\\b${escapeRegex(phrase)}\\b`, "gi");
    const matches = cleaned.match(pattern);
    if (matches?.length) {
      total += matches.length;
      if (!used.includes(phrase)) {
        used.push(phrase);
      }
    }
  }
  return { count: total, used };
}

export function computeWordsPerMinute(
  wordCount: number,
  durationSeconds: number | null
): number | null {
  if (durationSeconds === null || durationSeconds < 1 || wordCount <= 0) {
    return null;
  }
  return Math.round((wordCount / (durationSeconds / 60)) * 10) / 10;
}

export function buildSpeechMetrics(
  text: string,
  inputMode: InputMode,
  durationSeconds: number | null
): SpeechMetrics {
  const wordCount = countWords(text);
  const fillers = countFillerWords(text);
  const base: SpeechMetrics = {
    input_mode: inputMode,
    word_count: wordCount,
    filler_word_count: fillers.count,
    filler_words_used: fillers.used,
    duration_seconds: null,
    words_per_minute: null,
    speech_timing_available: false,
    disclaimer: SPEECH_METRICS_DISCLAIMER,
  };

  if (inputMode === "typed") {
    return base;
  }

  if (durationSeconds !== null && durationSeconds >= 1) {
    base.duration_seconds = Math.round(durationSeconds * 10) / 10;
    base.words_per_minute = computeWordsPerMinute(wordCount, durationSeconds);
    base.speech_timing_available = base.words_per_minute !== null;
  }

  return base;
}

export function isSpeechRecognitionSupported(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  const w = window as Window & {
    SpeechRecognition?: unknown;
    webkitSpeechRecognition?: unknown;
  };
  return Boolean(w.SpeechRecognition || w.webkitSpeechRecognition);
}
