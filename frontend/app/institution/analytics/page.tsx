"use client";

import { useCallback, useEffect, useState } from "react";

import { getApiErrorMessage } from "@/lib/api/errors";
import {
  fetchInstitutionAnalyticsDashboard,
  type InstitutionAnalyticsDashboard,
} from "@/lib/api/institution-analytics";
import { fetchMyInstitutionMemberships } from "@/lib/api/institutions";

export default function InstitutionAnalyticsPage() {
  const [institutionId, setInstitutionId] = useState<string | null>(null);
  const [dashboard, setDashboard] = useState<InstitutionAnalyticsDashboard | null>(null);
  const [department, setDepartment] = useState("");
  const [jobRole, setJobRole] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const memberships = await fetchMyInstitutionMemberships();
      const first = memberships[0];
      if (!first) return;
      setInstitutionId(first.institution.id);
      const data = await fetchInstitutionAnalyticsDashboard(first.institution.id, {
        department,
        job_role: jobRole,
      });
      setDashboard(data);
    } catch (e) {
      setError(getApiErrorMessage(e));
    }
  }, [department, jobRole]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!dashboard) {
    return <p className="text-sm text-slate-500">Loading analytics…</p>;
  }

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold text-slate-900">Institution analytics</h2>
        <p className="mt-1 text-xs text-slate-600">{dashboard.not_hiring_outcome_note}</p>
        <p className="text-xs text-slate-500">{dashboard.disclaimer}</p>
      </header>

      <div className="flex flex-wrap gap-2">
        <input
          value={department}
          onChange={(e) => setDepartment(e.target.value)}
          placeholder="Department filter"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
        <input
          value={jobRole}
          onChange={(e) => setJobRole(e.target.value)}
          placeholder="Job role filter"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          type="button"
          onClick={() => void load()}
          className="rounded-lg bg-brand-700 px-4 py-2 text-sm text-white"
        >
          Apply filters
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {dashboard.cards.map((card) => (
          <MetricCard key={card.label} card={card} />
        ))}
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-slate-800">Monthly activity</h3>
        <ul className="mt-3 space-y-2 text-sm">
          {dashboard.monthly_activity_trend.map((row) => (
            <li key={row.period} className="flex items-center gap-3">
              <span className="w-16 text-slate-500">{row.period}</span>
              <ActivityBar value={row.sessions} max={Math.max(...dashboard.monthly_activity_trend.map((r) => r.sessions), 1)} />
              <span>{row.sessions} sessions</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-semibold">Skill dimensions (avg / 5)</h3>
          <SkillBars distribution={dashboard.skill_distribution} />
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-semibold">Common skill gaps</h3>
          <ul className="mt-2 text-sm text-slate-700">
            {dashboard.common_skill_gaps.length === 0 ? (
              <li className="text-slate-500">Insufficient sample or no data.</li>
            ) : (
              dashboard.common_skill_gaps.map((gap) => (
                <li key={gap.concept}>
                  {gap.concept} · {gap.mention_count} mentions
                </li>
              ))
            )}
          </ul>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold">Cohort comparison</h3>
        <table className="mt-2 w-full text-left text-sm">
          <thead>
            <tr className="text-slate-500">
              <th className="py-1">Cohort</th>
              <th>n</th>
              <th>Sessions</th>
              <th>Avg score</th>
              <th>Assignments</th>
            </tr>
          </thead>
          <tbody>
            {dashboard.cohort_comparisons.map((c) => (
              <tr key={c.cohort_id} className="border-t border-slate-100">
                <td className="py-1">{c.cohort_name}</td>
                <td>{c.sample_size}</td>
                <td>{c.suppressed ? "—" : c.sessions_completed}</td>
                <td>{c.suppressed ? "—" : c.average_score ?? "—"}</td>
                <td>
                  {c.suppressed
                    ? "—"
                    : c.assignment_completion_rate != null
                      ? `${Math.round(c.assignment_completion_rate * 100)}%`
                      : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      {institutionId ? (
        <p className="text-xs text-slate-400">Reporting period: {dashboard.reporting_period.generated_at}</p>
      ) : null}
    </div>
  );
}

function MetricCard({
  card,
}: {
  card: InstitutionAnalyticsDashboard["cards"][number];
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{card.label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">
        {card.suppressed ? "—" : card.value ?? "—"}
      </p>
      {card.note ? <p className="mt-1 text-[11px] text-slate-500">{card.note}</p> : null}
    </div>
  );
}

function ActivityBar({ value, max }: { value: number; max: number }) {
  const width = Math.round((value / max) * 100);
  return (
    <div className="h-2 flex-1 rounded-full bg-slate-100">
      <div className="h-2 rounded-full bg-brand-600" style={{ width: `${width}%` }} />
    </div>
  );
}

function SkillBars({ distribution }: { distribution: Record<string, number> }) {
  const entries = Object.entries(distribution);
  if (entries.length === 0) {
    return <p className="mt-2 text-sm text-slate-500">Hidden for small samples.</p>;
  }
  return (
    <ul className="mt-2 space-y-2">
      {entries.map(([key, val]) => (
        <li key={key}>
          <div className="flex justify-between text-xs text-slate-600">
            <span>{key.replace(/_/g, " ")}</span>
            <span>{val}</span>
          </div>
          <div className="mt-1 h-2 rounded-full bg-slate-100">
            <div
              className="h-2 rounded-full bg-emerald-600"
              style={{ width: `${(val / 5) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
