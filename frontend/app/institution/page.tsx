"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { getApiErrorMessage } from "@/lib/api/errors";
import {
  createInstitution,
  fetchInstitutionAnalytics,
  fetchMyInstitutionMemberships,
  type InstitutionProfile,
} from "@/lib/api/institutions";

export default function InstitutionHomePage() {
  const [memberships, setMemberships] = useState<
    Awaited<ReturnType<typeof fetchMyInstitutionMemberships>>
  >([]);
  const [selected, setSelected] = useState<InstitutionProfile | null>(null);
  const [analytics, setAnalytics] = useState<Record<string, unknown> | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const rows = await fetchMyInstitutionMemberships();
      setMemberships(rows);
      if (rows[0]) {
        setSelected(rows[0].institution);
        const overview = await fetchInstitutionAnalytics(rows[0].institution.id);
        setAnalytics(overview);
      }
    } catch (loadError) {
      setError(getApiErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleCreate() {
    if (!name.trim()) return;
    setError(null);
    try {
      const inst = await createInstitution({ name: name.trim() });
      setName("");
      await load();
      setSelected(inst);
    } catch (createError) {
      setError(getApiErrorMessage(createError));
    }
  }

  if (loading) {
    return <p className="text-sm text-slate-500">Loading institutions…</p>;
  }

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-slate-900">Your institutions</h2>
        {memberships.length === 0 ? (
          <p className="mt-2 text-sm text-slate-600">
            You are not part of an institution yet. Create one for your placement cell or accept an
            invite from your college.
          </p>
        ) : (
          <ul className="mt-3 space-y-2 text-sm">
            {memberships.map((row) => (
              <li key={row.institution.id} className="flex justify-between gap-3">
                <span>
                  {row.institution.name} · {row.membership.role.replace("_", " ")}
                </span>
                <button
                  type="button"
                  className="text-brand-700"
                  onClick={() => {
                    setSelected(row.institution);
                    void fetchInstitutionAnalytics(row.institution.id).then(setAnalytics);
                  }}
                >
                  View
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="New institution name"
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          <button
            type="button"
            onClick={() => void handleCreate()}
            className="rounded-lg bg-brand-700 px-4 py-2 text-sm text-white"
          >
            Create institution
          </button>
        </div>
      </section>

      {selected && analytics ? (
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-900">{selected.name} — readiness overview</h2>
          <p className="mt-1 text-xs text-slate-500">
            {String(analytics.privacy_note ?? "")}
          </p>
          <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Students" value={String(analytics.student_count ?? 0)} />
            <Stat label="Cohorts" value={String(analytics.cohort_count ?? 0)} />
            <Stat
              label="Assignment completion"
              value={`${Math.round(Number(analytics.assignment_completion_rate ?? 0) * 100)}%`}
            />
            <Stat
              label="Avg interview score"
              value={
                analytics.average_interview_score != null
                  ? String(analytics.average_interview_score)
                  : "—"
              }
            />
          </dl>
          <Link
            href="/institution/reports"
            className="mt-4 inline-block text-sm text-brand-700"
          >
            Open reports & export →
          </Link>
        </section>
      ) : null}

      {error ? (
        <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="text-lg font-semibold text-slate-900">{value}</dd>
    </div>
  );
}
