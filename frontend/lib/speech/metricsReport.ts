import type { InputMode, SpeechMetrics } from "@/lib/speech/metrics";

/** Stable key for comparing whether parent notification is needed. */
export function metricsReportKey(
  metrics: SpeechMetrics,
  inputMode: InputMode
): string {
  return JSON.stringify({
    input_mode: inputMode,
    word_count: metrics.word_count,
    duration_seconds: metrics.duration_seconds,
    words_per_minute: metrics.words_per_minute,
    filler_word_count: metrics.filler_word_count,
    speech_timing_available: metrics.speech_timing_available,
  });
}
