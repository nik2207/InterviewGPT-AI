"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/ui/PageHeader";
import { getApiErrorMessage } from "@/lib/api/errors";
import { createInterviewSession } from "@/lib/api/interviews";
import { fetchResumes } from "@/lib/api/resumes";
import { buildCreateInterviewPayload } from "@/lib/interview/createSession";
import { LANGUAGE_LABELS } from "@/lib/speech/locales";
import {
  DEFAULT_INTERVIEW_LANGUAGE,
  type DifficultyLevel,
  type InterviewLanguageCode,
  type InterviewLanguageSettings,
  type InterviewType,
  type InterviewerTone,
} from "@/types/interview";
import type { ResumeMetadata } from "@/types/resume";

export default function InterviewSetupPage() {
  const router = useRouter();
  const [resumes, setResumes] = useState<ResumeMetadata[]>([]);
  const [resumeId, setResumeId] = useState("");
  const [role, setRole] = useState("Software Engineer");
  const [difficulty, setDifficulty] = useState<DifficultyLevel>("intermediate");
  const [interviewType, setInterviewType] =
    useState<InterviewType>("resume_based");
  const [questionCount, setQuestionCount] = useState(5);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [interviewerTone, setInterviewerTone] =
    useState<InterviewerTone>("professional");
  const [language, setLanguage] = useState<InterviewLanguageSettings>(
    DEFAULT_INTERVIEW_LANGUAGE
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchResumes()
      .then((data) => {
        setResumes(data.resumes);
        if (data.resumes[0]) {
          setResumeId(data.resumes[0].id);
        }
      })
      .catch(() => setError("Unable to load resumes."));
  }, []);

  async function handleStart() {
    if (!resumeId) {
      setError("Select a resume with a saved analysis.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const session = await createInterviewSession(
        buildCreateInterviewPayload({
          role,
          difficulty,
          interview_type: interviewType,
          resume_id: resumeId,
          question_count: questionCount,
          voice_interview_enabled: voiceEnabled,
          interviewer_tone: interviewerTone,
          language: {
            ...language,
            feedback_language: language.practice_professional_english
              ? "en"
              : language.feedback_language,
          },
        })
      );
      router.push(`/dashboard/interviews/${session.id}`);
    } catch (startError) {
      setError(getApiErrorMessage(startError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader
        title="Mock interview"
        description="Start a resume-based practice session using questions from your saved analysis."
      />

      <form
        className="app-card space-y-4 p-6"
        onSubmit={(event) => {
          event.preventDefault();
          handleStart();
        }}
      >
        <label className="block text-sm font-medium text-slate-700">
          Target role
          <input
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            required
          />
        </label>

        <label className="block text-sm font-medium text-slate-700">
          Resume
          <select
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            value={resumeId}
            onChange={(e) => setResumeId(e.target.value)}
          >
            <option value="">Select resume…</option>
            {resumes.map((resume) => (
              <option key={resume.id} value={resume.id}>
                {resume.original_filename}
              </option>
            ))}
          </select>
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm font-medium text-slate-700">
            Difficulty
            <select
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={difficulty}
              onChange={(e) =>
                setDifficulty(e.target.value as DifficultyLevel)
              }
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </label>

          <label className="block text-sm font-medium text-slate-700">
            Interview type
            <select
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={interviewType}
              onChange={(e) =>
                setInterviewType(e.target.value as InterviewType)
              }
            >
              <option value="resume_based">Resume-based</option>
              <option value="technical">Technical</option>
              <option value="behavioral">Behavioral / HR</option>
              <option value="mixed">Mixed</option>
            </select>
          </label>
        </div>

        <div className="rounded-lg border border-app-border bg-slate-50 p-4 space-y-3">
          <p className="text-sm font-semibold text-slate-800">Language practice</p>
          <div className="grid gap-3 sm:grid-cols-3">
            <LanguageSelect
              label="Question language"
              value={language.question_language}
              onChange={(code) =>
                setLanguage((prev) => ({ ...prev, question_language: code }))
              }
            />
            <LanguageSelect
              label="Answer language"
              value={language.answer_language}
              onChange={(code) =>
                setLanguage((prev) => ({ ...prev, answer_language: code }))
              }
            />
            <LanguageSelect
              label="Feedback language"
              value={language.feedback_language}
              onChange={(code) =>
                setLanguage((prev) => ({ ...prev, feedback_language: code }))
              }
              disabled={language.practice_professional_english}
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={language.allow_bilingual_answers}
              onChange={(e) =>
                setLanguage((prev) => ({
                  ...prev,
                  allow_bilingual_answers: e.target.checked,
                }))
              }
            />
            Allow bilingual answers (local language + English technical terms)
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={language.practice_professional_english}
              onChange={(e) =>
                setLanguage((prev) => ({
                  ...prev,
                  practice_professional_english: e.target.checked,
                  feedback_language: e.target.checked ? "en" : prev.feedback_language,
                }))
              }
            />
            Practise explaining technical concepts in professional English
          </label>
          <p className="text-xs text-slate-600">
            Browser speech recognition varies by language and device. Typed answers always
            work. Technical terms may stay in English in questions and feedback.
          </p>
        </div>

        <div className="rounded-lg border border-app-border bg-slate-50 p-4">
          <label className="flex items-center gap-2 text-sm font-medium text-slate-800">
            <input
              type="checkbox"
              checked={voiceEnabled}
              onChange={(e) => setVoiceEnabled(e.target.checked)}
            />
            AI voice interviewer mode
          </label>
          <p className="mt-1 text-xs text-slate-600">
            Sequential text-to-speech and browser speech-to-text — not full duplex voice chat.
            Typed fallback remains available.
          </p>
          {voiceEnabled ? (
            <label className="mt-3 block text-sm font-medium text-slate-700">
              Interviewer tone
              <select
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={interviewerTone}
                onChange={(e) =>
                  setInterviewerTone(e.target.value as InterviewerTone)
                }
              >
                <option value="friendly">Friendly</option>
                <option value="professional">Professional</option>
                <option value="challenging">Challenging</option>
              </select>
            </label>
          ) : null}
        </div>

        <label className="block text-sm font-medium text-slate-700">
          Questions (3–15)
          <input
            type="number"
            min={3}
            max={15}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            value={questionCount}
            onChange={(e) => {
              const next = Number(e.target.value);
              setQuestionCount(Number.isFinite(next) ? next : 5);
            }}
          />
        </label>

        {error ? (
          <p className="text-sm text-red-600" role="alert">{error}</p>
        ) : null}

        <div className="flex flex-wrap gap-3">
          <button
            type="submit"
            disabled={loading}
            className="btn-primary disabled:opacity-60"
          >
            {loading ? "Starting…" : "Start interview"}
          </button>
          <Link
            href="/dashboard/resumes"
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
          >
            Analyze resume first
          </Link>
        </div>
      </form>
    </div>
  );
}

function LanguageSelect({
  label,
  value,
  onChange,
  disabled = false,
}: {
  label: string;
  value: InterviewLanguageCode;
  onChange: (code: InterviewLanguageCode) => void;
  disabled?: boolean;
}) {
  return (
    <label className="block text-xs font-medium text-slate-600">
      {label}
      <select
        className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2 text-sm"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value as InterviewLanguageCode)}
      >
        {(Object.keys(LANGUAGE_LABELS) as InterviewLanguageCode[]).map((code) => (
          <option key={code} value={code}>
            {LANGUAGE_LABELS[code]}
          </option>
        ))}
      </select>
    </label>
  );
}
