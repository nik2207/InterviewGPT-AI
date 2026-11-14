"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";

import { InterviewFeedback } from "@/components/interviews/InterviewFeedback";
import { InterviewLanguageIndicators } from "@/components/interviews/InterviewLanguageIndicators";
import { DEFAULT_INTERVIEW_LANGUAGE } from "@/types/interview";
import {
  downloadInterviewReport,
  downloadInterviewTranscript,
  saveTranscriptPracticeRevision,
  updateTranscriptBookmarks,
} from "@/lib/api/interviews";
import type { InterviewTranscriptReview, TranscriptFilter } from "@/types/transcript";
import { FOLLOW_UP_TYPE_LABELS } from "@/types/transcript";

interface InterviewTranscriptReviewViewProps {
  sessionId: string;
  review: InterviewTranscriptReview;
  onReviewChange: (review: InterviewTranscriptReview) => void;
  onDeleted?: () => void;
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export function InterviewTranscriptReviewView({
  sessionId,
  review,
  onReviewChange,
  onDeleted,
}: InterviewTranscriptReviewViewProps) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<TranscriptFilter>("all");
  const [activeId, setActiveId] = useState<string | null>(
    review.items[0]?.question.id ?? null
  );
  const [practiceDrafts, setPracticeDrafts] = useState<Record<string, string>>(() => {
    const map: Record<string, string> = {};
    for (const item of review.items) {
      if (item.practice_revision) {
        map[item.question.id] = item.practice_revision.draft_text;
      }
    }
    return map;
  });
  const [savingPractice, setSavingPractice] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [reportDownloading, setReportDownloading] = useState(false);
  const [bookmarkBusy, setBookmarkBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const syncReview = useCallback(
    (next: InterviewTranscriptReview) => {
      onReviewChange(next);
    },
    [onReviewChange]
  );

  const filteredItems = useMemo(() => {
    const q = search.trim().toLowerCase();
    return review.items.filter((item) => {
      if (filter === "weak" && !item.is_weak) return false;
      if (filter === "bookmarked" && !item.is_bookmarked) return false;
      if (filter === "main" && item.question.is_follow_up) return false;
      if (filter === "follow_up" && !item.question.is_follow_up) return false;
      if (!q) return true;
      const haystack = [
        item.question.question,
        item.answer?.answer_text ?? "",
        item.question.category,
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [review.items, search, filter]);

  async function toggleBookmark(questionId: string) {
    setBookmarkBusy(true);
    setError(null);
    const next = new Set(review.bookmarks);
    if (next.has(questionId)) {
      next.delete(questionId);
    } else {
      next.add(questionId);
    }
    try {
      const updated = await updateTranscriptBookmarks(sessionId, [...next]);
      syncReview(updated);
    } catch {
      setError("Could not update bookmarks.");
    } finally {
      setBookmarkBusy(false);
    }
  }

  async function handleSavePractice(questionId: string) {
    const draft = (practiceDrafts[questionId] ?? "").trim();
    if (!draft) {
      setError("Enter a practice draft before saving.");
      return;
    }
    setSavingPractice(questionId);
    setError(null);
    try {
      const updated = await saveTranscriptPracticeRevision(sessionId, questionId, draft);
      syncReview(updated);
    } catch {
      setError("Could not save practice draft.");
    } finally {
      setSavingPractice(null);
    }
  }

  async function handleTranscriptExport() {
    setExporting(true);
    setError(null);
    try {
      const blob = await downloadInterviewTranscript(sessionId);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `interview-transcript-${sessionId.slice(0, 12)}.pdf`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Transcript export failed.");
    } finally {
      setExporting(false);
    }
  }

  async function handleScoreReportDownload() {
    setReportDownloading(true);
    setError(null);
    try {
      const blob = await downloadInterviewReport(sessionId);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `interview-report-${sessionId.slice(0, 12)}.pdf`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Score report download failed.");
    } finally {
      setReportDownloading(false);
    }
  }

  const activeItem =
    review.items.find((item) => item.question.id === activeId) ?? filteredItems[0] ?? null;

  return (
    <div className="mx-auto max-w-7xl space-y-4">
      <header className="app-card flex flex-wrap items-start justify-between gap-4 px-5 py-4">
        <div>
          <Link
            href={`/dashboard/interviews/history/${sessionId}`}
            className="text-sm text-app-primary hover:underline"
          >
            ← Session summary
          </Link>
          <h1 className="mt-2 text-2xl font-semibold text-app-ink">{review.role}</h1>
          <div className="mt-2">
            <InterviewLanguageIndicators
              settings={review.language_settings ?? DEFAULT_INTERVIEW_LANGUAGE}
              compact
            />
          </div>
          <p className="mt-1 text-sm text-app-muted">
            Transcript review · {review.items.length} questions in timeline order
          </p>
          <p className="mt-2 max-w-2xl text-xs text-app-muted">
            {review.text_transcript_disclaimer}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="btn-secondary"
            disabled={exporting}
            onClick={handleTranscriptExport}
          >
            {exporting ? "Exporting…" : "Export transcript PDF"}
          </button>
          {review.status === "completed" ? (
            <button
              type="button"
              className="btn-secondary"
              disabled={reportDownloading}
              onClick={handleScoreReportDownload}
            >
              {reportDownloading ? "Downloading…" : "Score report PDF"}
            </button>
          ) : null}
        </div>
      </header>

      {error ? (
        <p className="rounded-control border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}

      <div className="app-card px-4 py-3">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <input
            type="search"
            placeholder="Search questions and answers…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full max-w-md rounded-control border border-slate-200 px-3 py-2 text-sm"
            aria-label="Search transcript"
          />
          <div className="flex flex-wrap gap-2 text-sm">
            {(
              [
                ["all", "All"],
                ["weak", "Weak answers"],
                ["bookmarked", "Bookmarks"],
                ["main", "Main"],
                ["follow_up", "Follow-ups"],
              ] as const
            ).map(([value, label]) => (
              <button
                key={value}
                type="button"
                className={
                  filter === value
                    ? "rounded-full bg-app-primary px-3 py-1 text-white"
                    : "rounded-full border border-slate-200 px-3 py-1 text-app-muted"
                }
                onClick={() => setFilter(value)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(220px,280px)_1fr]">
        <nav className="app-card max-h-[70vh] overflow-y-auto p-3" aria-label="Question timeline">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-app-muted">
            Timeline
          </p>
          <ul className="space-y-1">
            {filteredItems.map((item) => (
              <li key={item.question.id}>
                <button
                  type="button"
                  onClick={() => setActiveId(item.question.id)}
                  className={`w-full rounded-control px-2 py-2 text-left text-sm ${
                    activeId === item.question.id
                      ? "bg-app-primary-soft text-app-primary"
                      : "hover:bg-slate-50"
                  }`}
                >
                  <span className="font-medium">#{item.sequence}</span>{" "}
                  {item.is_bookmarked ? "★ " : ""}
                  {item.is_weak ? (
                    <span className="text-amber-700">· weak</span>
                  ) : null}
                  <p className="line-clamp-2 text-xs text-app-muted">
                    {item.question.question}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <div className="space-y-4">
          {activeItem ? (
            <article
              id={`transcript-${activeItem.question.id}`}
              className={`app-card p-5 ${
                activeItem.is_weak ? "ring-2 ring-amber-200" : ""
              }`}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2 text-xs font-medium uppercase text-app-muted">
                    <span>#{activeItem.sequence}</span>
                    {activeItem.question.is_follow_up ? (
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-900">
                        Follow-up
                        {activeItem.question.follow_up_type
                          ? ` · ${FOLLOW_UP_TYPE_LABELS[activeItem.question.follow_up_type]}`
                          : ""}
                      </span>
                    ) : (
                      <span>Main</span>
                    )}
                    {activeItem.is_weak ? (
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-900">
                        Needs improvement
                      </span>
                    ) : null}
                    {activeItem.answer_status === "skipped" ? (
                      <span className="text-slate-500">Skipped</span>
                    ) : null}
                  </div>
                  <h2 className="mt-2 text-lg font-medium text-app-ink">
                    {activeItem.question.question}
                  </h2>
                </div>
                <button
                  type="button"
                  disabled={bookmarkBusy}
                  onClick={() => toggleBookmark(activeItem.question.id)}
                  className="btn-secondary text-sm"
                  aria-pressed={activeItem.is_bookmarked}
                >
                  {activeItem.is_bookmarked ? "Bookmarked" : "Bookmark"}
                </button>
              </div>

              {activeItem.answer?.answer_text ? (
                <div className="mt-4 rounded-control bg-slate-50 p-3">
                  <p className="text-xs font-semibold text-app-muted">Your answer</p>
                  <p className="mt-1 text-sm text-app-ink whitespace-pre-wrap">
                    {activeItem.answer.answer_text}
                  </p>
                  {activeItem.timing?.timing_reliable &&
                  activeItem.timing.duration_seconds != null ? (
                    <p className="mt-2 text-xs text-app-muted">
                      Spoken duration: {formatDuration(activeItem.timing.duration_seconds)}
                      {activeItem.timing.words_per_minute != null
                        ? ` · ${Math.round(activeItem.timing.words_per_minute)} WPM`
                        : ""}
                    </p>
                  ) : activeItem.timing?.submitted_at ? (
                    <p className="mt-2 text-xs text-app-muted">
                      Submitted {new Date(activeItem.timing.submitted_at).toLocaleString()}
                    </p>
                  ) : null}
                </div>
              ) : activeItem.answer_status === "skipped" ? (
                <p className="mt-4 text-sm text-app-muted">This follow-up was skipped.</p>
              ) : (
                <p className="mt-4 text-sm text-app-muted">No answer recorded.</p>
              )}

              {activeItem.voice_transcript.length > 0 ? (
                <div className="mt-4">
                  <p className="text-xs font-semibold text-app-muted">Voice transcript (text)</p>
                  <ul className="mt-2 space-y-2">
                    {activeItem.voice_transcript.map((entry, index) => (
                      <li
                        key={`${entry.created_at}-${index}`}
                        className="rounded-control border border-slate-100 px-3 py-2 text-sm"
                      >
                        <span className="text-xs font-medium uppercase text-app-primary">
                          {entry.role}
                          {entry.language ? ` · ${entry.language}` : ""}
                        </span>
                        <p className="mt-1 whitespace-pre-wrap text-app-ink">{entry.text}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {activeItem.answer?.evaluation ? (
                <div className="mt-4">
                  <InterviewFeedback
                    evaluation={activeItem.answer.evaluation}
                    originalAnswer={activeItem.answer.answer_text}
                    onPracticeImprovement={() => {
                      const prompt =
                        activeItem.answer?.evaluation?.improvement_coach
                          ?.follow_up_practice_question;
                      if (prompt) {
                        setPracticeDrafts((prev) => ({
                          ...prev,
                          [activeItem.question.id]: prev[activeItem.question.id] ?? "",
                        }));
                        document
                          .getElementById(`practice-${activeItem.question.id}`)
                          ?.scrollIntoView({ behavior: "smooth" });
                      }
                    }}
                  />
                </div>
              ) : null}

              <div
                id={`practice-${activeItem.question.id}`}
                className="mt-6 rounded-control border border-app-primary/20 bg-app-primary-soft/30 p-4"
              >
                <h3 className="text-sm font-semibold text-app-ink">Practice revision</h3>
                <p className="mt-1 text-xs text-app-muted">
                  Rewrite your answer for practice. This does not change your official interview
                  record.
                </p>
                <textarea
                  className="mt-3 w-full rounded-control border border-slate-200 p-3 text-sm"
                  rows={5}
                  value={practiceDrafts[activeItem.question.id] ?? ""}
                  onChange={(e) =>
                    setPracticeDrafts((prev) => ({
                      ...prev,
                      [activeItem.question.id]: e.target.value,
                    }))
                  }
                  placeholder="Draft an improved answer…"
                />
                <button
                  type="button"
                  className="btn-primary mt-2"
                  disabled={savingPractice === activeItem.question.id}
                  onClick={() => handleSavePractice(activeItem.question.id)}
                >
                  {savingPractice === activeItem.question.id ? "Saving…" : "Save practice draft"}
                </button>
              </div>
            </article>
          ) : (
            <p className="text-sm text-app-muted">No items match your filters.</p>
          )}
        </div>
      </div>

      <footer className="app-card px-4 py-3 text-xs text-app-muted">
        <p>{review.audio_retention_policy}</p>
        {onDeleted ? (
          <button
            type="button"
            className="mt-3 text-sm text-red-600 hover:underline"
            onClick={onDeleted}
          >
            Delete this interview session…
          </button>
        ) : null}
      </footer>
    </div>
  );
}
