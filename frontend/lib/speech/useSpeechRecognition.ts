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

  // Accumulates all final transcript segments across result events and
  // browser-initiated recognition restarts within a single user session.
  const finalTranscriptRef = useRef<string>("");
  // True while the user has explicitly started recording and not yet stopped.
  const isListeningRef = useRef<boolean>(false);
  // Tracks the current recognition instance so onend can restart it.
  const recognitionLangRef = useRef<string>(recognitionLang);

  // Keep lang ref in sync so the restart inside onend picks up the latest lang.
  useEffect(() => {
    recognitionLangRef.current = recognitionLang;
  }, [recognitionLang]);

  useEffect(() => {
    return () => {
      isListeningRef.current = false;
      recognitionRef.current?.stop();
    };
  }, []);

  // Extracted so onend can call it to restart after browser VAD stops the session.
  const startRecognition = useCallback(
    (RecognitionCtor: new () => SpeechRecognition) => {
      const recognition = new RecognitionCtor();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = recognitionLangRef.current;

      recognition.onstart = () => {
        // Only record start time on the very first segment of a user session.
        if (startedAtRef.current === null) {
          startedAtRef.current = Date.now();
        }
        setPermissionState("listening");
        setErrorMessage(null);
      };

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        // Accumulate all final segments into the ref; collect any in-progress
        // interim text so the textarea always shows the complete answer.
        let interimTranscript = "";

        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const result = event.results[i];
          if (result.isFinal) {
            finalTranscriptRef.current +=
              (finalTranscriptRef.current ? " " : "") +
              result[0].transcript.trim();
          } else {
            interimTranscript += result[0].transcript;
          }
        }

        const combined =
          finalTranscriptRef.current +
          (interimTranscript
            ? (finalTranscriptRef.current ? " " : "") +
              interimTranscript.trim()
            : "");

        onTranscript(combined.trim());
      };

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        if (event.error === "not-allowed") {
          isListeningRef.current = false;
          setPermissionState("denied");
          setErrorMessage("Microphone permission denied. Use typed answers.");
        } else if (event.error === "no-speech") {
          // Browser detected no speech for ~3 s — do not treat as a hard error;
          // onend will fire next and restart if the user is still listening.
        } else {
          isListeningRef.current = false;
          setPermissionState("error");
          setErrorMessage("Speech recognition error. You can continue typing.");
        }
      };

      recognition.onend = () => {
        // If the user is still in a listening session, restart recognition
        // immediately — this handles the browser's built-in VAD cutting the
        // stream mid-sentence (common on Chrome even with continuous=true).
        if (isListeningRef.current) {
          try {
            const w = window as Window & {
              SpeechRecognition?: new () => SpeechRecognition;
              webkitSpeechRecognition?: new () => SpeechRecognition;
            };
            const Ctor = w.SpeechRecognition || w.webkitSpeechRecognition;
            if (Ctor) {
              startRecognition(Ctor);
              return; // Duration stays open; new instance takes over.
            }
          } catch {
            // Fall through to end the session on error.
          }
        }

        // User explicitly stopped or restart failed — finalise duration.
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
      recognition.start();
    },
    [onTranscript]
  );

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

    // Reset accumulators for a fresh session.
    finalTranscriptRef.current = "";
    startedAtRef.current = null;
    isListeningRef.current = true;

    try {
      startRecognition(RecognitionCtor);
    } catch {
      isListeningRef.current = false;
      setPermissionState("error");
      setErrorMessage("Unable to start speech recognition.");
    }
  }, [supported, startRecognition]);

  const stop = useCallback(() => {
    isListeningRef.current = false;
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
