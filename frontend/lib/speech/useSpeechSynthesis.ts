"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { InterviewerTone } from "@/types/interview";

const TONE_VOICE_PARAMS: Record<
  InterviewerTone,
  { rate: number; pitch: number }
> = {
  friendly: { rate: 0.95, pitch: 1.05 },
  professional: { rate: 1.0, pitch: 1.0 },
  challenging: { rate: 1.05, pitch: 0.92 },
};

export function isSpeechSynthesisSupported(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

export function useSpeechSynthesis() {
  const [supported] = useState(() => isSpeechSynthesisSupported());
  const [speaking, setSpeaking] = useState(false);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  const cancel = useCallback(() => {
    if (!supported) {
      return;
    }
    window.speechSynthesis.cancel();
    setSpeaking(false);
  }, [supported]);

  const speak = useCallback(
    (
      text: string,
      tone: InterviewerTone = "professional",
      lang = "en-US"
    ) => {
      if (!supported || !text.trim()) {
        return;
      }
      cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      const params = TONE_VOICE_PARAMS[tone];
      utterance.lang = lang;
      utterance.rate = params.rate;
      utterance.pitch = params.pitch;
      utterance.onstart = () => setSpeaking(true);
      utterance.onend = () => setSpeaking(false);
      utterance.onerror = () => setSpeaking(false);
      utteranceRef.current = utterance;
      window.speechSynthesis.speak(utterance);
    },
    [supported, cancel]
  );

  useEffect(() => () => cancel(), [cancel]);

  return { supported, speaking, speak, cancel };
}
