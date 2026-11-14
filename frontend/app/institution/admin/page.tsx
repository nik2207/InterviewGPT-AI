"use client";

import { useCallback, useEffect, useState } from "react";

import { getApiErrorMessage } from "@/lib/api/errors";
import {
  fetchAdminMembers,
  fetchInstitutionAuditLog,
  fetchInstitutionSubscription,
} from "@/lib/api/institution-analytics";
import { fetchMyInstitutionMemberships } from "@/lib/api/institutions";
import { apiClient } from "@/lib/api/client";

export default function InstitutionAdminPage() {
  const [institutionId, setInstitutionId] = useState<string | null>(null);
  const [subscription, setSubscription] = useState<Awaited<
    ReturnType<typeof fetchInstitutionSubscription>
  > | null>(null);
  const [members, setMembers] = useState<Array<Record<string, unknown>>>([]);
  const [audit, setAudit] = useState<Array<{ action: string; created_at: string }>>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const memberships = await fetchMyInstitutionMemberships();
      const first = memberships[0];
      if (!first) return;
      setInstitutionId(first.institution.id);
      const [sub, mem, log] = await Promise.all([
        fetchInstitutionSubscription(first.institution.id),
        fetchAdminMembers(first.institution.id),
        fetchInstitutionAuditLog(first.institution.id),
      ]);
      setSubscription(sub);
      setMembers(mem.items);
      setAudit(log.items);
    } catch (e) {
      setError(getApiErrorMessage(e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function removeMember(membershipId: string) {
    if (!institutionId) return;
  await apiClient.post(
      `/institutions/${institutionId}/admin/members/${membershipId}/remove`
    );
    await load();
  }

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-slate-900">Administration</h2>

      {subscription ? (
        <section className="rounded-xl border border-slate-200 bg-white p-4 text-sm">
          <h3 className="font-semibold">Institution subscription</h3>
          <p className="mt-1 text-slate-600">{subscription.disclaimer}</p>
          <p className="mt-2">
            Plan: <strong>{subscription.subscription_plan}</strong> · Seats{" "}
            {subscription.seats_used}/{subscription.seat_limit}
          </p>
        </section>
      ) : null}

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold">Members (paginated)</h3>
        <ul className="mt-2 space-y-1 text-sm">
          {members.map((m) => (
            <li key={String(m.id)} className="flex justify-between gap-2 border-b py-1">
              <span>
                {String(m.user_id)} · {String(m.role)}
              </span>
              {m.status === "active" && m.role !== "institution_admin" ? (
                <button
                  type="button"
                  className="text-red-600"
                  onClick={() => void removeMember(String(m.id))}
                >
                  Remove
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold">Audit log</h3>
        <ul className="mt-2 text-xs text-slate-600">
          {audit.map((row, i) => (
            <li key={`${row.action}-${i}`}>
              {row.action} · {new Date(row.created_at).toLocaleString()}
            </li>
          ))}
        </ul>
      </section>

      {error ? <p className="text-sm text-red-700">{error}</p> : null}
    </div>
  );
}
