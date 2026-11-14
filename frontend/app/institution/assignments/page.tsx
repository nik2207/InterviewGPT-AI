"use client";

import { useCallback, useEffect, useState } from "react";

import { getApiErrorMessage } from "@/lib/api/errors";
import {
  createAssignment,
  fetchAssignments,
  fetchMyInstitutionMemberships,
} from "@/lib/api/institutions";

export default function InstitutionAssignmentsPage() {
  const [institutionId, setInstitutionId] = useState<string | null>(null);
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const memberships = await fetchMyInstitutionMemberships();
    const first = memberships[0];
    if (!first) return;
    setInstitutionId(first.institution.id);
    setItems(await fetchAssignments(first.institution.id));
  }, []);

  useEffect(() => {
    void load().catch((e) => setError(getApiErrorMessage(e)));
  }, [load]);

  async function handleCreate() {
    if (!institutionId || !title.trim()) return;
    try {
      await createAssignment(institutionId, {
        title: title.trim(),
        activity_type: "mock_interview",
      });
      setTitle("");
      await load();
    } catch (e) {
      setError(getApiErrorMessage(e));
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Preparation assignments</h2>
      <ul className="rounded-xl border border-slate-200 bg-white p-4 text-sm">
        {items.map((row) => (
          <li key={String(row.id)} className="border-b border-slate-100 py-2">
            {String(row.title)} · {String(row.activity_type)} · completed{" "}
            {Number(row.completion_count ?? 0)}/{Number(row.assigned_count ?? 0)}
          </li>
        ))}
      </ul>
      <div className="flex gap-2">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Assignment title"
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          type="button"
          onClick={() => void handleCreate()}
          className="rounded-lg bg-brand-700 px-4 py-2 text-sm text-white"
        >
          Assign activity
        </button>
      </div>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
    </div>
  );
}
