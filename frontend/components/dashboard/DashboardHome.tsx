"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ScoreTrendChart } from "@/components/dashboard/ScoreTrendChart";
import { StatCard } from "@/components/dashboard/StatCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import {
  fetchDashboardStats,
  fetchRecentInterviewActivity,
  fetchScoreTrend,
  fetchSkillGapInsights,
  type SkillGapInsight,
} from "@/lib/api/dashboard";
import type { ScoreTrendPoint } from "@/lib/api/dashboard";
import type { DashboardStats, InterviewActivityItem } from "@/types/dashboard";
import type { UserProfile } from "@/types/user";

interface DashboardHomeProps {
  user: UserProfile;
}

function formatCount(value: number | null): string {
  return value === null ? "—" : String(value);
}

function formatScore(value: number | null): string {
  return value === null ? "—" : `${value}/100`;
}

export function DashboardHome({ user }: DashboardHomeProps) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [activity, setActivity] = useState<InterviewActivityItem[] | null>(null);
  const [trend, setTrend] = useState<ScoreTrendPoint[] | null>(null);
  const [gaps, setGaps] = useState<SkillGapInsight[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [statsResult, activityResult, trendResult, gapsResult] =
          await Promise.all([
            fetchDashboardStats(),
            fetchRecentInterviewActivity(),
            fetchScoreTrend(),
            fetchSkillGapInsights(),
          ]);
        if (!cancelled) {
          setStats(statsResult);
          setActivity(activityResult);
          setTrend(trendResult);
          setGaps(gapsResult);
        }
      } catch {
        if (!cancelled) {
          setError("Unable to load dashboard data right now.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const firstName = user.name?.split(" ")[0] || "there";
  const hasCompleted = (stats?.interviewsCompleted ?? 0) > 0;

  const recommendations = [
    !hasCompleted
      ? {
          title: "Start your first mock interview",
          body: "Practice with resume-based questions and AI feedback.",
          href: "/dashboard/interviews",
          cta: "Start interview",
        }
      : null,
    {
      title: "Analyse or upload a resume",
      body: "Get tailored skills, gaps and interview questions.",
      href: "/dashboard/resumes",
      cta: "Resume workspace",
    },
    hasCompleted
      ? {
          title: "Review insights & reports",
          body: "Open history, scores and downloadable PDF reports.",
          href: "/dashboard/interviews/history",
          cta: "View history",
        }
      : null,
    hasCompleted
      ? {
          title: "Open preparation plan",
          body: "Coaching recommendations from your latest interview evidence.",
          href: "/dashboard/career",
          cta: "Preparation plan",
        }
      : null,
  ].filter(Boolean) as Array<{
    title: string;
    body: string;
    href: string;
    cta: string;
  }>;

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <section className="app-card overflow-hidden p-6 sm:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-sm font-medium text-app-primary">Welcome back</p>
            <h1 className="mt-1 text-2xl font-semibold text-app-ink sm:text-3xl">
              Hi {firstName}, ready to practise?
            </h1>
            <p className="mt-2 max-w-xl text-sm text-app-muted">
              Your personal interview preparation workspace — track sessions,
              scores and focus areas from real mock interviews.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/dashboard/interviews" className="btn-primary">
              Start mock interview
            </Link>
            <Link href="/dashboard/career" className="btn-secondary">
              Preparation plan
            </Link>
          </div>
        </div>
      </section>

      {error ? (
        <div className="rounded-control border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900" role="alert">
          {error}
        </div>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-3">
        <div className="app-card p-6 lg:col-span-2">
          <h2 className="text-lg font-semibold text-app-ink">Readiness overview</h2>
          <p className="mt-1 text-sm text-app-muted">
            Based on completed, evaluated mock interviews. Not a hiring prediction.
          </p>
          {loading ? (
            <LoadingSkeleton rows={1} className="mt-4 h-24" />
          ) : (
            <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-4xl font-semibold tabular-nums text-app-ink">
                  {formatScore(stats?.averageScore ?? null)}
                </p>
                <p className="mt-1 text-sm text-app-muted">
                  {hasCompleted
                    ? `Average across ${stats?.interviewsCompleted} completed interview(s)`
                    : "Not enough data yet — complete a mock interview"}
                </p>
              </div>
              <div className="rounded-control bg-app-primary-soft px-4 py-3 text-sm text-app-primary">
                {hasCompleted
                  ? `${stats?.practiceSessions} practice session(s) started`
                  : "Upload a resume and run analysis to unlock richer insights"}
              </div>
            </div>
          )}
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
          {loading ? (
            <LoadingSkeleton rows={2} className="h-24" />
          ) : (
            <>
              <StatCard
                label="Completed"
                value={formatCount(stats?.interviewsCompleted ?? null)}
                helper="Finished mock interviews"
                accent="primary"
                icon={<span>◎</span>}
              />
              <StatCard
                label="Practice sessions"
                value={formatCount(stats?.practiceSessions ?? null)}
                helper="Started (in progress + done)"
                icon={<span>▣</span>}
              />
            </>
          )}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <div className="app-card p-6 xl:col-span-2">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-lg font-semibold text-app-ink">Recent interviews</h2>
            <Link
              href="/dashboard/interviews/history"
              className="text-sm font-medium text-app-primary hover:underline"
            >
              View all
            </Link>
          </div>
          {loading ? (
            <LoadingSkeleton className="mt-4 h-16" rows={3} />
          ) : activity && activity.length > 0 ? (
            <ul className="mt-4 divide-y divide-app-border">
              {activity.map((item) => (
                <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                  <div>
                    <p className="font-medium text-app-ink">{item.title}</p>
                    <p className="text-xs text-app-muted">
                      {item.completedAt}
                      {item.questionCount ? ` · ${item.questionCount} questions` : ""}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-semibold tabular-nums text-app-primary">
                      {item.score !== null ? `${item.score}/100` : "—"}
                    </span>
                    <Link
                      href={`/dashboard/interviews/history/${item.id}/review`}
                      className="text-sm text-app-muted hover:text-app-primary"
                    >
                      Report
                    </Link>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              title="No completed interviews yet"
              description="Start a mock interview to see activity and scores here."
              actionLabel="Start mock interview"
              actionHref="/dashboard/interviews"
            />
          )}
        </div>

        <div className="app-card p-6">
          <h2 className="text-lg font-semibold text-app-ink">Score trend</h2>
          <p className="mt-1 text-sm text-app-muted">Recent completed sessions</p>
          <div className="mt-4">
            {loading ? (
              <LoadingSkeleton rows={1} className="h-40" />
            ) : (
              <ScoreTrendChart points={trend ?? []} />
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="app-card p-6">
          <h2 className="text-lg font-semibold text-app-ink">Skill gaps & focus</h2>
          <p className="mt-1 text-sm text-app-muted">
            From your most recent evaluated mock interview (when available).
          </p>
          {loading ? (
            <LoadingSkeleton className="mt-4 h-14" rows={3} />
          ) : gaps && gaps.length > 0 ? (
            <ul className="mt-4 space-y-3">
              {gaps.map((gap) => (
                <li
                  key={gap.evidence}
                  className="rounded-control border border-app-border px-3 py-2"
                >
                  <p className="text-sm font-medium text-app-ink">{gap.label}</p>
                  <p className="mt-1 text-xs text-app-muted">{gap.evidence}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm text-app-muted">
              Complete a mock interview or analyse a resume to surface improvement
              areas.
            </p>
          )}
        </div>

        <div className="app-card p-6">
          <h2 className="text-lg font-semibold text-app-ink">Recommended next steps</h2>
          <ul className="mt-4 space-y-3">
            {recommendations.map((rec) => (
              <li
                key={rec.href}
                className="rounded-control border border-app-border p-4 transition hover:border-app-primary/40"
              >
                <p className="font-medium text-app-ink">{rec.title}</p>
                <p className="mt-1 text-sm text-app-muted">{rec.body}</p>
                <Link
                  href={rec.href}
                  className="mt-3 inline-block text-sm font-semibold text-app-primary hover:underline"
                >
                  {rec.cta} →
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
