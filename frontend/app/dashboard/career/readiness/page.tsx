"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import { CareerReadinessView } from "@/components/career/CareerReadinessView";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  downloadCareerReadinessPdf,
  fetchCareerReadinessReport,
  generateCareerReadinessReport,
} from "@/lib/api/careerReadiness";
import { fetchJobMatches } from "@/lib/api/jobMatch";
import { fetchResumeAnalysis, fetchResumes } from "@/lib/api/resumes";
import type { CareerReadinessReport } from "@/types/careerReadiness";
import type { JobMatchListItem } from "@/types/jobMatch";
import type { ResumeMetadata } from "@/types/resume";

function ReadinessPageContent() {
  const searchParams = useSearchParams();
  const reportId = searchParams.get("reportId");

  const [resumes, setResumes] = useState<ResumeMetadata[]>([]);
  const [analysedIds, setAnalysedIds] = useState<string[]>([]);
  const [jobMatches, setJobMatches] = useState<JobMatchListItem[]>([]);
  const [selectedResume, setSelectedResume] = useState("");
  const [selectedMatch, setSelectedMatch] = useState("");
  const [report, setReport] = useState<CareerReadinessReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function init() {
      setLoading(true);
      try {
        const [resumeList, matches] = await Promise.all([
          fetchResumes(),
          fetchJobMatches(),
        ]);
        setResumes(resumeList.resumes);
        setJobMatches(matches);
        const analysed: string[] = [];
        for (const resume of resumeList.resumes) {
          try {
            await fetchResumeAnalysis(resume.id);
            analysed.push(resume.id);
          } catch {
            /* skip */
          }
        }
        setAnalysedIds(analysed);
        const defaultResume = analysed[0] ?? resumeList.resumes[0]?.id ?? "";
        setSelectedResume(defaultResume);
        const matchForResume = matches.find((m) => m.resume_id === defaultResume);
        if (matchForResume) {
          setSelectedMatch(matchForResume.id);
        }
        if (reportId) {
          setReport(await fetchCareerReadinessReport(reportId));
        }
      } catch {
        setError("Unable to load readiness workspace.");
      } finally {
        setLoading(false);
      }
    }
    init();
  }, [reportId]);

  const handleGenerate = useCallback(async () => {
    if (!selectedResume) {
      return;
    }
    setGenerating(true);
    setError(null);
    try {
      const result = await generateCareerReadinessReport({
        resume_id: selectedResume,
        job_match_id: selectedMatch || undefined,
      });
      setReport(result);
      window.history.replaceState(
        null,
        "",
        `/dashboard/career/readiness?reportId=${result.id}`
      );
    } catch {
      setError("Could not generate report.");
    } finally {
      setGenerating(false);
    }
  }, [selectedResume, selectedMatch]);

  const handleDownload = useCallback(async () => {
    if (!report) {
      return;
    }
    setDownloading(true);
    try {
      const blob = await downloadCareerReadinessPdf(report.id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `career-readiness-${report.id.slice(0, 12)}.pdf`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("PDF download failed.");
    } finally {
      setDownloading(false);
    }
  }, [report]);

  const matchesForResume = jobMatches.filter((m) => m.resume_id === selectedResume);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        title="Career readiness report"
        description="Evidence-based scoring from your saved interviews, resume, job match, and preparation plan."
      />
      <Link href="/dashboard/career" className="text-sm text-app-primary hover:underline">
        ← Career workspace
      </Link>

      {error ? (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}

      <section className="app-card p-6">
        <h2 className="text-lg font-semibold text-app-ink">Generate report</h2>
        {loading ? (
          <LoadingSkeleton rows={2} className="mt-4 h-16" />
        ) : (
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-medium text-app-ink">
              Resume
              <select
                className="mt-1 block w-full rounded-control border border-app-border px-3 py-2 text-sm"
                value={selectedResume}
                onChange={(e) => {
                  setSelectedResume(e.target.value);
                  setSelectedMatch("");
                }}
              >
                {resumes.map((r) => (
                  <option key={r.id} value={r.id} disabled={!analysedIds.includes(r.id)}>
                    {r.original_filename}
                    {!analysedIds.includes(r.id) ? " (not analysed)" : ""}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-medium text-app-ink">
              Job match (optional)
              <select
                className="mt-1 block w-full rounded-control border border-app-border px-3 py-2 text-sm"
                value={selectedMatch}
                onChange={(e) => setSelectedMatch(e.target.value)}
              >
                <option value="">General readiness (no JD)</option>
                {matchesForResume.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.job_title} ({m.match_score}%)
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}
        <button
          type="button"
          className="btn-primary mt-4"
          disabled={generating || !analysedIds.includes(selectedResume)}
          onClick={handleGenerate}
        >
          {generating ? "Building report…" : "Generate readiness report"}
        </button>
        {!analysedIds.length ? (
          <p className="mt-2 text-sm text-app-muted">
            Upload and analyse a resume to begin.
          </p>
        ) : null}
      </section>

      {report ? (
        <CareerReadinessView
          report={report}
          onDownloadPdf={handleDownload}
          downloading={downloading}
        />
      ) : !loading ? (
        <EmptyState
          title="No readiness report yet"
          description="Complete mock interviews and optionally add a job match for a fuller score breakdown."
        />
      ) : null}
    </div>
  );
}

export default function CareerReadinessPage() {
  return (
    <Suspense fallback={<LoadingSkeleton rows={4} className="mx-auto max-w-6xl h-40" />}>
      <ReadinessPageContent />
    </Suspense>
  );
}
