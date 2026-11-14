"use client";

import { useEffect, useState } from "react";

import { getApiErrorMessage } from "@/lib/api/errors";
import { fetchInstitutionAnalytics, fetchMyInstitutionMemberships } from "@/lib/api/institutions";
import { apiClient } from "@/lib/api/client";

export default function InstitutionReportsPage() {
  const [institutionId, setInstitutionId] = useState<string | null>(null);
  const [analytics, setAnalytics] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const memberships = await fetchMyInstitutionMemberships();
        const first = memberships[0];
        if (!first) return;
        setInstitutionId(first.institution.id);
        setAnalytics(await fetchInstitutionAnalytics(first.institution.id));
      } catch (e) {
        setError(getApiErrorMessage(e));
      }
    })();
  }, []);

  async function downloadCsv() {
    if (!institutionId) return;
    const response = await apiClient.get(`/institutions/${institutionId}/reports/export`, {
      params: { report_type: "summary", export_format: "csv" },
      responseType: "blob",
    });
    const url = URL.createObjectURL(response.data);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `institution-${institutionId}-aggregate.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Reports & export</h2>
      <p className="text-sm text-slate-600">
        Exports contain aggregate metrics only (counts and averages). No resume or transcript
        content is included.
      </p>
      {analytics ? (
        <pre className="overflow-auto rounded-xl border bg-white p-4 text-xs">
          {JSON.stringify(analytics, null, 2)}
        </pre>
      ) : null}
      <button
        type="button"
        disabled={!institutionId}
        onClick={() => void downloadCsv()}
        className="rounded-lg border border-slate-300 px-4 py-2 text-sm disabled:opacity-50"
      >
        Download aggregate CSV
      </button>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
    </div>
  );
}
