"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { fetchInterviewHistory } from "@/lib/api/interviews";
import type { InterviewHistoryItem } from "@/types/interview";

export default function InterviewHistoryPage() {
  const [items, setItems] = useState<InterviewHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchInterviewHistory()
      .then(setItems)
      .catch(() => setError("Unable to load interview history."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <p className="text-sm text-slate-500" aria-live="polite">
        Loading history…
      </p>
    );
  }

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-semibold text-slate-900">Interview history</h1>
      <p className="mt-2 text-sm text-slate-600">
        Completed mock interviews, newest first.
      </p>

      {error ? (
        <p className="mt-4 text-sm text-red-600" role="alert">{error}</p>
      ) : null}

      {!error && items.length === 0 ? (
        <p className="mt-6 rounded-xl border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-600">
          No completed interviews yet.{" "}
          <Link href="/dashboard/interviews" className="text-brand-700 hover:underline">
            Start a mock interview
          </Link>
          .
        </p>
      ) : null}

      <ul className="mt-6 space-y-3">
        {items.map((item) => (
          <li key={item.id}>
            <Link
              href={`/dashboard/interviews/history/${item.id}/review`}
              className="block rounded-xl border border-slate-200 bg-white p-4 shadow-card hover:border-brand-200"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium text-slate-900">{item.role}</p>
                <p className="text-sm text-brand-700">
                  {item.overall_score !== null
                    ? `${item.overall_score}/100`
                    : "Score unavailable"}
                </p>
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {new Date(item.completed_at).toLocaleString()} ·{" "}
                {item.question_count} questions · {item.difficulty}
              </p>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
