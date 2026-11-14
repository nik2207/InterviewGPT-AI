"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { isSpeechRecognitionSupported } from "@/lib/speech/metrics";

export type SpeechPermissionState =
  | "unsupported"
  | "idle"
  | "listening"
  | "denied"
  | "error";

interface UseSpeechRecognitionOptions {
  onTranscript: (text: string) => void;
  /** BCP-47 locale, e.g. en-US */
  recognitionLang?: string;
}

export function useSpeechRecognition({
  onTranscript,
  recognitionLang = "en-US",
}: UseSpeechRecognitionOptions) {
  const [supported] = useState(() => isSpeechRecognitionSupported());
  const [permissionState, setPermissionState] =
    useState<SpeechPermissionState>(supported ? "idle" : "unsupported");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const startedAtRef = useRef<number | null>(null);
  const [durationSeconds, setDurationSeconds] = useState<number | null>(null);

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
    };
  }, []);

  const start = useCallback(() => {
    if (!supported) {
      setPermissionState("unsupported");
      return;
    }

    const w = window as Window & {
      SpeechRecognition?: new () => SpeechRecognition;
      webkitSpeechRecognition?: new () => SpeechRecognition;
    };
    const RecognitionCtor = w.SpeechRecognition || w.webkitSpeechRecognition;
    if (!RecognitionCtor) {
      setPermissionState("unsupported");
      return;
    }

    const recognition = new RecognitionCtor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = recognitionLang;

    recognition.onstart = () => {
      startedAtRef.current = Date.now();
      setPermissionState("listening");
      setErrorMessage(null);
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let transcript = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        transcript += event.results[i][0].transcript;
      }
      onTranscript(transcript.trim());
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      if (event.error === "not-allowed") {
        setPermissionState("denied");
        setErrorMessage("Microphone permission denied. Use typed answers.");
      } else {
        setPermissionState("error");
        setErrorMessage("Speech recognition error. You can continue typing.");
      }
      recognition.stop();
    };

    recognition.onend = () => {
      if (startedAtRef.current) {
        const seconds = (Date.now() - startedAtRef.current) / 1000;
        setDurationSeconds(seconds >= 1 ? seconds : null);
        startedAtRef.current = null;
      }
      setPermissionState((prev) =>
        prev === "listening" || prev === "idle" ? "idle" : prev
      );
    };

    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch {
      setPermissionState("error");
      setErrorMessage("Unable to start speech recognition.");
    }
  }, [onTranscript, supported, recognitionLang]);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  return {
    supported,
    permissionState,
    errorMessage,
    durationSeconds,
    start,
    stop,
  };
}
