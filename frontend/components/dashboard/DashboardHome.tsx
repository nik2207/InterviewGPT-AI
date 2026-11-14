"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { StatCard } from "@/components/dashboard/StatCard";
import {
  fetchDashboardStats,
  fetchRecentInterviewActivity,
} from "@/lib/api/dashboard";
import type { DashboardStats, InterviewActivityItem } from "@/types/dashboard";
import type { UserProfile } from "@/types/user";

interface DashboardHomeProps {
  user: UserProfile;
}

function formatMetric(value: number | null, suffix = ""): string {
  if (value === null) {
    return "—";
  }
  return `${value}${suffix}`;
}

export function DashboardHome({ user }: DashboardHomeProps) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [activity, setActivity] = useState<InterviewActivityItem[] | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [statsResult, activityResult] = await Promise.all([
          fetchDashboardStats(),
          fetchRecentInterviewActivity(),
        ]);
        if (!cancelled) {
          setStats(statsResult);
          setActivity(activityResult);
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

  return (
    <div className="space-y-8">
      <section
        className="rounded-2xl border border-brand-100 bg-gradient-to-br from-brand-50 to-white p-6 sm:p-8"
        aria-labelledby="welcome-heading"
      >
        <h1
          id="welcome-heading"
          className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl"
        >
          Welcome back, {firstName}
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-600 sm:text-base">
          Prepare for your next interview with AI-guided mock sessions, resume
          feedback, and targeted practice. Your workspace is ready when you are.
        </p>
        <div className="mt-6">
          <button
            type="button"
            className="inline-flex items-center justify-center rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
            aria-label="Start mock interview"
          >
            Start Mock Interview
          </button>
          <p className="mt-2 text-xs text-slate-500">
            Mock interview flow will be available in a future release.
          </p>
        </div>
      </section>

      {error ? (
        <div
          className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
          role="alert"
        >
          {error}
        </div>
      ) : null}

      <section aria-labelledby="stats-heading">
        <h2 id="stats-heading" className="text-lg font-semibold text-slate-900">
          Your snapshot
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Metrics appear here once interview analytics endpoints are connected.
        </p>
        {loading ? (
          <div
            className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
            aria-label="Loading statistics"
            aria-busy="true"
          >
            {Array.from({ length: 4 }).map((_, index) => (
              <div
                key={index}
                className="h-32 animate-pulse rounded-xl bg-slate-100"
              />
            ))}
          </div>
        ) : (
          <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Interviews completed"
              value={formatMetric(stats?.interviewsCompleted ?? null)}
              helper="No completed sessions yet"
              icon={<span>🎯</span>}
            />
            <StatCard
              label="Practice sessions"
              value={formatMetric(stats?.practiceSessions ?? null)}
              helper="Schedule your first practice"
              icon={<span>📝</span>}
            />
            <StatCard
              label="Average score"
              value={formatMetric(stats?.averageScore ?? null)}
              helper="Scores available after interviews"
              icon={<span>⭐</span>}
            />
            <StatCard
              label="Preparation progress"
              value={formatMetric(
                stats?.preparationProgressPercent ?? null,
                stats?.preparationProgressPercent === null ? "" : "%"
              )}
              helper="Track progress as you practice"
              icon={<span>📈</span>}
            />
          </div>
        )}
      </section>

      <section id="quick-actions" aria-labelledby="quick-actions-heading">
        <h2
          id="quick-actions-heading"
          className="text-lg font-semibold text-slate-900"
        >
          Quick actions
        </h2>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          {[
            {
              title: "Resume Analysis",
              body: "Upload a resume and get tailored feedback.",
            },
            {
              title: "Interview History",
              body: "Review past mock interviews and scores.",
            },
            {
              title: "Question Practice",
              body: "Drill common questions by role and level.",
            },
          ].map((action) => {
            const isResume = action.title === "Resume Analysis";
            const className =
              "rounded-xl border border-slate-200 bg-white p-5 text-left shadow-card transition hover:border-brand-200 hover:bg-brand-50/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600";

            if (isResume) {
              return (
                <Link
                  key={action.title}
                  href="/dashboard/resumes"
                  className={className}
                >
                  <h3 className="font-medium text-slate-900">{action.title}</h3>
                  <p className="mt-2 text-sm text-slate-600">{action.body}</p>
                  <p className="mt-3 text-xs font-medium text-brand-700">
                    Upload PDF
                  </p>
                </Link>
              );
            }

            return (
              <button
                key={action.title}
                type="button"
                className={className}
                aria-label={`${action.title} — coming soon`}
              >
                <h3 className="font-medium text-slate-900">{action.title}</h3>
                <p className="mt-2 text-sm text-slate-600">{action.body}</p>
                <p className="mt-3 text-xs font-medium text-brand-700">
                  Coming soon
                </p>
              </button>
            );
          })}
        </div>
      </section>

      <section
        id="activity"
        className="grid gap-6 lg:grid-cols-5"
        aria-labelledby="activity-heading"
      >
        <div className="lg:col-span-3">
          <h2
            id="activity-heading"
            className="text-lg font-semibold text-slate-900"
          >
            Recent interview activity
          </h2>
          <div className="mt-4 rounded-xl border border-slate-200 bg-white p-6 shadow-card">
            {loading ? (
              <div className="h-24 animate-pulse rounded-lg bg-slate-100" />
            ) : activity && activity.length > 0 ? (
              <ul className="space-y-3">
                {activity.map((item) => (
                  <li
                    key={item.id}
                    className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2"
                  >
                    <span className="text-sm font-medium text-slate-800">
                      {item.title}
                    </span>
                    <span className="text-xs text-slate-500">
                      {item.completedAt}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-center">
                <p className="text-sm font-medium text-slate-800">
                  No interviews yet
                </p>
                <p className="mt-1 text-sm text-slate-500">
                  Start a mock interview to see your activity and feedback here.
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="lg:col-span-2">
          <h2 className="text-lg font-semibold text-slate-900">
            Preparation progress
          </h2>
          <div className="mt-4 rounded-xl border border-slate-200 bg-white p-6 shadow-card">
            <p className="text-sm text-slate-600">
              Complete mock interviews and practice sessions to build a
              personalized preparation plan.
            </p>
            <div className="mt-4">
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span>Overall readiness</span>
                <span>Not available</span>
              </div>
              <div
                className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={0}
                aria-label="Preparation progress"
              >
                <div className="h-full w-0 rounded-full bg-brand-500" />
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
