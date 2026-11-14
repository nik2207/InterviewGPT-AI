"use client";

import { useCallback, useEffect, useState } from "react";

import { getApiErrorMessage } from "@/lib/api/errors";
import { createCohort, fetchCohorts, fetchMyInstitutionMemberships } from "@/lib/api/institutions";

export default function InstitutionCohortsPage() {
  const [institutionId, setInstitutionId] = useState<string | null>(null);
  const [cohorts, setCohorts] = useState<Array<Record<string, unknown>>>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const memberships = await fetchMyInstitutionMemberships();
    const first = memberships[0];
    if (!first) return;
    setInstitutionId(first.institution.id);
    setCohorts(await fetchCohorts(first.institution.id));
  }, []);

  useEffect(() => {
    void load().catch((e) => setError(getApiErrorMessage(e)));
  }, [load]);

  async function handleCreate() {
    if (!institutionId || !name.trim()) return;
    try {
      await createCohort(institutionId, { name: name.trim() });
      setName("");
      await load();
    } catch (e) {
      setError(getApiErrorMessage(e));
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Cohorts & batches</h2>
      <div className="flex gap-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Cohort name"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          type="button"
          onClick={() => void handleCreate()}
          className="rounded-lg bg-brand-700 px-4 py-2 text-sm text-white"
        >
          Create cohort
        </button>
      </div>
      <ul className="rounded-xl border border-slate-200 bg-white p-4 text-sm">
        {cohorts.map((c) => (
          <li key={String(c.id)} className="py-1">
            {String(c.name)} · {Number(c.member_count ?? 0)} students
          </li>
        ))}
      </ul>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
    </div>
  );
}
