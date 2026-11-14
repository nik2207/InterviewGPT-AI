"use client";

import { useCallback, useEffect, useState } from "react";

import { getApiErrorMessage } from "@/lib/api/errors";
import {
  fetchMyInstitutionMemberships,
  fetchStudentProgress,
  updateSharingConsent,
} from "@/lib/api/institutions";

export default function InstitutionStudentsPage() {
  const [institutionId, setInstitutionId] = useState<string | null>(null);
  const [myMembershipId, setMyMembershipId] = useState<string | null>(null);
  const [rows, setRows] = useState<Awaited<ReturnType<typeof fetchStudentProgress>>>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const memberships = await fetchMyInstitutionMemberships();
      const first = memberships[0];
      if (!first) return;
      setInstitutionId(first.institution.id);
      setMyMembershipId(first.membership.id);
      const progress = await fetchStudentProgress(first.institution.id);
      setRows(progress);
    } catch (loadError) {
      setError(getApiErrorMessage(loadError));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggleConsent(enabled: boolean) {
    if (!institutionId || !myMembershipId) return;
    await updateSharingConsent(institutionId, myMembershipId, enabled);
    await load();
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-900">Student progress</h2>
      <p className="text-sm text-slate-600">
        Aggregate readiness only — resumes, transcripts and answers are never shown here unless a
        student opts in to share progress metrics.
      </p>
      {myMembershipId ? (
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            onChange={(e) => void toggleConsent(e.target.checked)}
          />
          I am a student: allow trainers/officers to view my progress metrics
        </label>
      ) : null}
      {rows.length === 0 ? (
        <p className="text-sm text-slate-500">No visible student progress yet.</p>
      ) : (
        <ul className="space-y-2 rounded-xl border border-slate-200 bg-white p-4 text-sm">
          {rows.map((row) => (
            <li key={row.user_id} className="flex justify-between border-b border-slate-100 pb-2">
              <span>{row.display_name}</span>
              <span className="text-slate-600">
                Interviews {row.interviews_completed} · Assignments {row.assignments_completed}
              </span>
            </li>
          ))}
        </ul>
      )}
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
    </div>
  );
}
