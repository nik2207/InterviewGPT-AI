import type { InterviewLanguageCode } from "@/types/interview";

export const LANGUAGE_LABELS: Record<InterviewLanguageCode, string> = {
  en: "English",
  hi: "Hindi",
  mr: "Marathi",
};

/** BCP-47 tags passed to browser SpeechRecognition / SpeechSynthesis. */
export const SPEECH_BCP47: Record<InterviewLanguageCode, string> = {
  en: "en-US",
  hi: "hi-IN",
  mr: "mr-IN",
};

export type SpeechRecognitionSupportHint =
  | "widely_supported"
  | "often_supported"
  | "limited_support";

export const SPEECH_RECOGNITION_HINTS: Record<
  InterviewLanguageCode,
  SpeechRecognitionSupportHint
> = {
  en: "widely_supported",
  hi: "often_supported",
  mr: "limited_support",
};

export function speechRecognitionHintMessage(
  code: InterviewLanguageCode
): string | null {
  const hint = SPEECH_RECOGNITION_HINTS[code];
  if (hint === "widely_supported") {
    return null;
  }
  if (hint === "often_supported") {
    return "Hindi speech recognition depends on your browser and OS. You can always type your answer.";
  }
  return "Marathi speech recognition is not available in many browsers. Please use typed answers or try Hindi/English speech if supported.";
}
