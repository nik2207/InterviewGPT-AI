"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { InterviewFeedback } from "@/components/interviews/InterviewFeedback";
import { InterviewSummary } from "@/components/interviews/InterviewSummary";
import {
  downloadInterviewReport,
  fetchInterviewSession,
} from "@/lib/api/interviews";
import type { InterviewSession } from "@/types/interview";

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

export default function InterviewHistoryDetailPage() {
  const params = useParams<{ sessionId: string }>();
  const sessionId = params.sessionId;
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchInterviewSession(sessionId);
      if (data.status !== "completed") {
        setError("This interview is not completed yet.");
        setSession(null);
        return;
      }
      setSession(data);
    } catch (loadError) {
      setError(getErrorMessage(loadError));
      setSession(null);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleDownload() {
    setDownloading(true);
    setDownloadError(null);
    try {
      const blob = await downloadInterviewReport(sessionId);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `interview-report-${sessionId.slice(0, 12)}.pdf`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (downloadErr) {
      setDownloadError(getErrorMessage(downloadErr));
    } finally {
      setDownloading(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-slate-500">Loading interview…</p>;
  }

  if (!session) {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        <p className="text-sm text-red-600" role="alert">
          {error ?? "Interview not found."}
        </p>
        <Link href="/dashboard/interviews/history" className="text-sm text-brand-700">
          Back to history
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link
            href="/dashboard/interviews/history"
            className="text-sm text-brand-700 hover:underline"
          >
            ← History
          </Link>
          <h1 className="mt-2 text-2xl font-semibold text-slate-900">
            {session.role}
          </h1>
          <p className="text-sm text-slate-600">
            Completed {session.completed_at
              ? new Date(session.completed_at).toLocaleString()
              : "—"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href={`/dashboard/interviews/history/${sessionId}/review`}
            className="rounded-lg border border-brand-600 px-4 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50"
          >
            Transcript &amp; replay
          </Link>
          <button
            type="button"
            onClick={handleDownload}
            disabled={downloading}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {downloading ? "Preparing PDF…" : "Download PDF report"}
          </button>
        </div>
      </div>

      {downloadError ? (
        <p className="text-sm text-red-600" role="alert">{downloadError}</p>
      ) : null}

      <InterviewSummary session={session} />

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-card">
        <h2 className="text-sm font-semibold text-slate-900">Questions &amp; answers</h2>
        <ul className="mt-3 space-y-6">
          {session.answers.map((answer) => {
            const question = session.questions.find(
              (q) => q.id === answer.question_id
            );
            return (
              <li key={answer.submission_id} className="border-t border-slate-100 pt-4">
                <p className="text-sm font-medium text-slate-900">
                  {question?.question ?? "Question"}
                </p>
                <p className="mt-2 text-sm text-slate-700">{answer.answer_text}</p>
                {answer.speech_metrics ? (
                  <p className="mt-2 text-xs text-slate-500">
                    Input: {answer.speech_metrics.input_mode} · Words:{" "}
                    {answer.speech_metrics.word_count ?? "—"} · WPM:{" "}
                    {answer.speech_metrics.words_per_minute ?? "unavailable"}
                  </p>
                ) : null}
                {answer.evaluation ? (
                  <div className="mt-3">
                    <InterviewFeedback
                      evaluation={answer.evaluation}
                      originalAnswer={answer.answer_text}
                    />
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-slate-500">Evaluation unavailable</p>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
