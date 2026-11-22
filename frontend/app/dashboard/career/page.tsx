"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { JobMatchResults } from "@/components/career/JobMatchResults";
import { PageHeader } from "@/components/ui/PageHeader";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { fetchCoachingPlan, type CoachingPlanResponse } from "@/lib/api/coaching";
import { createJobMatch, fetchJobMatches } from "@/lib/api/jobMatch";
import {
  fetchPreparationPlans,
  generatePreparationPlan,
} from "@/lib/api/preparationPlan";
import { fetchInterviewHistory } from "@/lib/api/interviews";
import { fetchResumeAnalysis, fetchResumes } from "@/lib/api/resumes";
import { getApiErrorMessage } from "@/lib/api/errors";
import type { PreparationPlanListItem } from "@/types/preparationPlan";
import type { JobMatchListItem, JobMatchResult } from "@/types/jobMatch";
import type { InterviewHistoryItem } from "@/types/interview";
import type { ResumeMetadata } from "@/types/resume";

export default function CareerWorkspacePage() {
  const router = useRouter();
  const [resumes, setResumes] = useState<ResumeMetadata[]>([]);
  const [analysedResumeIds, setAnalysedResumeIds] = useState<string[]>([]);
  const [history, setHistory] = useState<InterviewHistoryItem[]>([]);
  const [savedMatches, setSavedMatches] = useState<JobMatchListItem[]>([]);
  const [selectedSession, setSelectedSession] = useState("");
  const [selectedResumeId, setSelectedResumeId] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [matchResult, setMatchResult] = useState<JobMatchResult | null>(null);
  const [plan, setPlan] = useState<CoachingPlanResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [matchLoading, setMatchLoading] = useState(false);
  const [planLoading, setPlanLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [matchError, setMatchError] = useState<string | null>(null);
  const [savedPlans, setSavedPlans] = useState<PreparationPlanListItem[]>([]);
  const [selectedJobMatchId, setSelectedJobMatchId] = useState("");
  const [dailyStudyMinutes, setDailyStudyMinutes] = useState(45);
  const [sevenDayLoading, setSevenDayLoading] = useState(false);
  const [sevenDayError, setSevenDayError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchResumes(),
      fetchInterviewHistory(),
      fetchJobMatches(),
      fetchPreparationPlans(),
    ])
      .then(async ([resumeData, historyData, matches, plans]) => {
        setResumes(resumeData.resumes);
        setHistory(historyData);
        setSavedMatches(matches);
        setSavedPlans(plans);
        if (matches[0]) {
          setSelectedJobMatchId(matches[0].id);
        }
        if (historyData[0]) {
          setSelectedSession(historyData[0].id);
        }
        const analysed: string[] = [];
        await Promise.all(
          resumeData.resumes.map(async (resume) => {
            try {
              await fetchResumeAnalysis(resume.id);
              analysed.push(resume.id);
            } catch {
              /* no analysis yet */
            }
          })
        );
        setAnalysedResumeIds(analysed);
        const defaultResume =
          analysed[0] ?? resumeData.resumes[0]?.id ?? "";
        setSelectedResumeId(defaultResume);
      })
      .catch(() => setError("Unable to load career workspace data."))
      .finally(() => setLoading(false));
  }, []);

  async function loadPlan() {
    if (!selectedSession) {
      return;
    }
    setPlanLoading(true);
    setError(null);
    try {
      const result = await fetchCoachingPlan(selectedSession);
      setPlan(result);
    } catch (cause: unknown) {
      setError(getApiErrorMessage(cause));
      setPlan(null);
    } finally {
      setPlanLoading(false);
    }
  }

  async function runSevenDayPlan() {
    if (!selectedResumeId || !analysedResumeIds.includes(selectedResumeId)) {
      setSevenDayError("Select an analysed resume first.");
      return;
    }
    setSevenDayLoading(true);
    setSevenDayError(null);
    try {
      const created = await generatePreparationPlan({
        resume_id: selectedResumeId,
        job_match_id: selectedJobMatchId || undefined,
        daily_study_minutes: dailyStudyMinutes,
      });
      router.push(`/dashboard/career/plan?planId=${created.id}`);
    } catch (cause: unknown) {
      setSevenDayError(getApiErrorMessage(cause));
    } finally {
      setSevenDayLoading(false);
    }
  }

  async function runJobMatch() {
    if (!selectedResumeId || jobDescription.trim().length < 80) {
      setMatchError("Select an analysed resume and paste a job description (80+ characters).");
      return;
    }
    setMatchLoading(true);
    setMatchError(null);
    try {
      const result = await createJobMatch({
        resume_id: selectedResumeId,
        job_description: jobDescription.trim(),
        job_title: jobTitle.trim() || undefined,
      });
      setMatchResult(result);
      setSavedMatches((items) => [
        {
          id: result.id,
          resume_id: result.resume_id,
          job_title: result.job_title,
          match_score: result.score.match_score,
          status: result.status,
          created_at: result.created_at,
        },
        ...items,
      ]);
    } catch {
      setMatchError("Job match failed. Check that the resume is analysed and try again.");
      setMatchResult(null);
    } finally {
      setMatchLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        title="Career preparation"
        description="Match your resume to a role, see skill gaps, and practise with targeted questions."
      />
      <Link
        href="/dashboard/career/readiness"
        className="inline-block text-sm font-medium text-app-primary hover:underline"
      >
        Open career readiness report →
      </Link>

      {error ? (
        <p className="text-sm text-red-600" role="alert">{error}</p>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="app-card p-6">
          <h2 className="text-lg font-semibold text-app-ink">AI job description match</h2>
          {loading ? (
            <LoadingSkeleton rows={3} className="mt-4 h-28" />
          ) : (
            <>
              <p className="mt-2 text-sm text-app-muted">
                {analysedResumeIds.length > 0
                  ? "Pick an analysed resume and paste a job description."
                  : "Upload and analyse a resume before running job match."}
              </p>
              <label className="mt-4 block text-sm font-medium text-app-ink">
                Resume
                <select
                  className="mt-1 block w-full rounded-control border border-app-border px-3 py-2 text-sm"
                  value={selectedResumeId}
                  onChange={(e) => setSelectedResumeId(e.target.value)}
                >
                  {resumes.map((resume) => (
                    <option key={resume.id} value={resume.id} disabled={!analysedResumeIds.includes(resume.id)}>
                      {resume.original_filename}
                      {!analysedResumeIds.includes(resume.id) ? " (not analysed)" : ""}
                    </option>
                  ))}
                </select>
              </label>
              <label className="mt-4 block text-sm font-medium text-app-ink">
                Job title (optional)
                <input
                  className="mt-1 block w-full rounded-control border border-app-border px-3 py-2 text-sm"
                  value={jobTitle}
                  onChange={(e) => setJobTitle(e.target.value)}
                  placeholder="e.g. Senior Backend Engineer"
                />
              </label>
              <label className="mt-4 block text-sm font-medium text-app-ink">
                Job description
                <textarea
                  className="mt-2 min-h-[140px] w-full rounded-control border border-app-border px-3 py-2 text-sm"
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                  placeholder="Paste the full job description…"
                />
              </label>
              {matchError ? (
                <p className="mt-2 text-sm text-red-600" role="alert">{matchError}</p>
              ) : null}
              <button
                type="button"
                className="btn-primary mt-4"
                disabled={matchLoading || analysedResumeIds.length === 0}
                onClick={runJobMatch}
              >
                {matchLoading ? "Analysing match…" : "Run job match"}
              </button>
              <Link href="/dashboard/resumes" className="btn-secondary mt-3 ml-0 inline-block sm:ml-3">
                Manage resumes
              </Link>
            </>
          )}
        </section>

        <section className="app-card p-6">
          <h2 className="text-lg font-semibold text-app-ink">Saved job matches</h2>
          {loading ? (
            <LoadingSkeleton rows={2} className="mt-4 h-16" />
          ) : savedMatches.length === 0 ? (
            <p className="mt-3 text-sm text-app-muted">No saved matches yet.</p>
          ) : (
            <ul className="mt-4 space-y-2">
              {savedMatches.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    className="w-full rounded-control border border-app-border px-3 py-2 text-left text-sm hover:border-app-primary"
                    onClick={() => router.push(`/dashboard/career/matches/${item.id}`)}
                  >
                    <span className="font-medium text-app-ink">{item.job_title}</span>
                    <span className="ml-2 text-app-primary">{item.match_score}%</span>
                    <span className="block text-xs text-app-muted">
                      {new Date(item.created_at).toLocaleString()}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {matchResult ? (
        <section className="app-card p-6">
          <JobMatchResults result={matchResult} />
        </section>
      ) : null}

      <section className="app-card p-6">
        <h2 className="text-lg font-semibold text-app-ink">7-day preparation plan</h2>
        <p className="mt-1 text-sm text-app-muted">
          Uses resume analysis, optional job match, and interview feedback. Tasks save to your
          account as you complete them.
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="text-sm font-medium text-app-ink">
            Daily study time (minutes)
            <input
              type="number"
              min={15}
              max={240}
              className="mt-1 block w-full rounded-control border border-app-border px-3 py-2 text-sm"
              value={dailyStudyMinutes}
              onChange={(e) => setDailyStudyMinutes(Number(e.target.value))}
            />
          </label>
          <label className="text-sm font-medium text-app-ink">
            Job match (optional)
            <select
              className="mt-1 block w-full rounded-control border border-app-border px-3 py-2 text-sm"
              value={selectedJobMatchId}
              onChange={(e) => setSelectedJobMatchId(e.target.value)}
            >
              <option value="">None</option>
              {savedMatches.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.job_title} ({m.match_score}%)
                </option>
              ))}
            </select>
          </label>
        </div>
        {sevenDayError ? (
          <p className="mt-2 text-sm text-red-600" role="alert">
            {sevenDayError}
          </p>
        ) : null}
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            className="btn-primary"
            disabled={sevenDayLoading || analysedResumeIds.length === 0}
            onClick={runSevenDayPlan}
          >
            {sevenDayLoading ? "Generating…" : "Generate 7-day plan"}
          </button>
          {savedPlans[0] ? (
            <Link href={`/dashboard/career/plan?planId=${savedPlans[0].id}`} className="btn-secondary">
              Open latest plan ({savedPlans[0].progress_percent}%)
            </Link>
          ) : null}
        </div>
      </section>

      <section className="app-card p-6">
        <h2 className="text-lg font-semibold text-app-ink">Skills snapshot</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div className="rounded-control border border-app-border p-4">
            <p className="text-xs font-semibold uppercase text-app-muted">Skills you have</p>
            <p className="mt-2 text-sm text-app-muted">
              View extracted skills from resume analysis after you upload a PDF.
            </p>
            <Link href="/dashboard/resumes" className="mt-3 inline-block text-sm text-app-primary">
              View analysis →
            </Link>
          </div>
          <div className="rounded-control border border-app-border p-4">
            <p className="text-xs font-semibold uppercase text-app-muted">Skills to learn</p>
            <p className="mt-2 text-sm text-app-muted">
              Run job match above or review interview evaluations for gap insights.
            </p>
          </div>
        </div>
      </section>

      <section className="app-card p-6">
        <h2 className="text-lg font-semibold text-app-ink">AI preparation plan</h2>
        <p className="mt-1 text-sm text-app-muted">
          Powered by your saved interview evidence and resume analysis (LangGraph workflow).
        </p>
        {history.length === 0 ? (
          <p className="mt-4 text-sm text-app-muted">
            Complete a mock interview first to generate a coaching plan.
          </p>
        ) : (
          <div className="mt-4 flex flex-wrap items-end gap-3">
            <label className="text-sm font-medium text-app-ink">
              Based on interview
              <select
                className="mt-1 block min-w-[220px] rounded-control border border-app-border px-3 py-2 text-sm"
                value={selectedSession}
                onChange={(e) => setSelectedSession(e.target.value)}
              >
                {history.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.role} — {new Date(item.completed_at).toLocaleDateString()}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="btn-primary"
              disabled={planLoading}
              onClick={loadPlan}
            >
              {planLoading ? "Generating…" : "Generate plan"}
            </button>
          </div>
        )}
        {plan ? (
          <div className="mt-6 space-y-4 border-t border-app-border pt-4">
            {plan.status !== "completed" || !plan.plan ? (
              <p className="text-sm text-amber-800">
                {plan.message ?? "Plan could not be generated."}
              </p>
            ) : (
              <>
                <p className="text-sm text-app-ink">{plan.plan.summary}</p>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <p className="text-xs font-semibold uppercase text-app-muted">Focus areas</p>
                    <ul className="mt-2 list-disc pl-5 text-sm text-app-ink">
                      {plan.plan.recommended_focus_areas.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase text-app-muted">
                      Practice suggestions
                    </p>
                    <ul className="mt-2 list-disc pl-5 text-sm text-app-ink">
                      {plan.plan.practice_suggestions.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </>
            )}
            <p className="text-xs text-app-muted">{plan.disclaimer}</p>
          </div>
        ) : null}
      </section>

      <section className="app-card p-6">
        <h2 className="text-lg font-semibold text-app-ink">Learning resources</h2>
        <p className="mt-2 text-sm text-app-muted">
          Curated course links are not integrated. Use job-match gap summaries and coaching
          focus areas to choose topics to study.
        </p>
      </section>
    </div>
  );
}
