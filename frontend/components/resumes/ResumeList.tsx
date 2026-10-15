"use client";

import type { ResumeMetadata } from "@/types/resume";

interface ResumeListProps {
  resumes: ResumeMetadata[];
  loading: boolean;
  error: string | null;
  selectedResumeId: string | null;
  analyzingResumeId: string | null;
  onAnalyze: (resumeId: string, refresh?: boolean) => void;
  onViewAnalysis: (resumeId: string) => void;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  return `${(bytes / 1024).toFixed(1)} KB`;
}

export function ResumeList({
  resumes,
  loading,
  error,
  selectedResumeId,
  analyzingResumeId,
  onAnalyze,
  onViewAnalysis,
}: ResumeListProps) {
  if (loading) {
    return (
      <div
        className="rounded-xl border border-slate-200 bg-white p-6 shadow-card"
        aria-busy="true"
        aria-label="Loading uploaded resumes"
      >
        <div className="h-24 animate-pulse rounded-lg bg-slate-100" />
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900"
        role="alert"
      >
        {error}
      </div>
    );
  }

  if (resumes.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center shadow-card">
        <p className="text-sm font-medium text-slate-800">No resumes uploaded</p>
        <p className="mt-2 text-sm text-slate-500">
          Upload a PDF resume to prepare for AI feedback and tailored interview
          practice.
        </p>
      </div>
    );
  }

  return (
    <section
      className="rounded-xl border border-slate-200 bg-white p-6 shadow-card"
      aria-labelledby="resume-list-heading"
    >
      <h2
        id="resume-list-heading"
        className="text-lg font-semibold text-slate-900"
      >
        Your uploaded resumes
      </h2>
      <ul className="mt-4 space-y-3">
        {resumes.map((resume) => {
          const isSelected = selectedResumeId === resume.id;
          const isAnalyzing = analyzingResumeId === resume.id;

          return (
            <li
              key={resume.id}
              className={`rounded-lg border px-4 py-3 ${
                isSelected
                  ? "border-brand-200 bg-brand-50/40"
                  : "border-slate-100"
              }`}
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-900">
                    {resume.original_filename}
                  </p>
                  <p className="text-xs text-slate-500">
                    {formatSize(resume.file_size_bytes)} · {resume.page_count}{" "}
                    page{resume.page_count === 1 ? "" : "s"} ·{" "}
                    {resume.parsing_status}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Uploaded {formatDate(resume.uploaded_at)}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => onAnalyze(resume.id, false)}
                    disabled={isAnalyzing}
                    className="rounded-lg bg-brand-600 px-3 py-2 text-xs font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isAnalyzing ? "Analyzing…" : "Analyze resume"}
                  </button>
                  <button
                    type="button"
                    onClick={() => onAnalyze(resume.id, true)}
                    disabled={isAnalyzing}
                    className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
                  >
                    Fresh analysis
                  </button>
                  <button
                    type="button"
                    onClick={() => onViewAnalysis(resume.id)}
                    className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
                  >
                    View saved
                  </button>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
