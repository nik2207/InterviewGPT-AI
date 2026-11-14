"use client";

import { useCallback, useEffect, useState } from "react";

import { getApiErrorMessage } from "@/lib/api/errors";
import {
  fetchInstitutionMembers,
  fetchMyInstitutionMemberships,
  inviteInstitutionMember,
  type InstitutionRole,
} from "@/lib/api/institutions";

export default function InstitutionRolesPage() {
  const [institutionId, setInstitutionId] = useState<string | null>(null);
  const [members, setMembers] = useState<Awaited<ReturnType<typeof fetchInstitutionMembers>>>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<InstitutionRole>("student");
  const [inviteLink, setInviteLink] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const memberships = await fetchMyInstitutionMemberships();
    const first = memberships[0];
    if (!first) return;
    setInstitutionId(first.institution.id);
    setMembers(await fetchInstitutionMembers(first.institution.id));
  }, []);

  useEffect(() => {
    void load().catch((e) => setError(getApiErrorMessage(e)));
  }, [load]);

  async function handleInvite() {
    if (!institutionId || !email.trim()) return;
    try {
      const result = await inviteInstitutionMember(institutionId, { email: email.trim(), role });
      setInviteLink(
        result.invite_token
          ? `${window.location.origin}/institution/join?token=${encodeURIComponent(result.invite_token)}`
          : null
      );
      setEmail("");
      await load();
    } catch (e) {
      setError(getApiErrorMessage(e));
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Membership & roles</h2>
      <ul className="rounded-xl border border-slate-200 bg-white p-4 text-sm">
        {members.map((member) => (
          <li key={member.id} className="flex justify-between border-b border-slate-100 py-1">
            <span>{member.user_id}</span>
            <span className="text-slate-600">{member.role}</span>
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap gap-2">
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Invite email"
          className="min-w-[12rem] flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
        <select
          value={role}
          onChange={(e) => setRole(e.target.value as InstitutionRole)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="student">Student</option>
          <option value="trainer">Trainer</option>
          <option value="placement_officer">Placement officer</option>
          <option value="institution_admin">Institution admin</option>
        </select>
        <button
          type="button"
          onClick={() => void handleInvite()}
          className="rounded-lg bg-brand-700 px-4 py-2 text-sm text-white"
        >
          Send invite
        </button>
      </div>
      {inviteLink ? (
        <p className="text-xs text-slate-600">
          Share invite link: <span className="break-all font-mono">{inviteLink}</span>
        </p>
      ) : null}
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
    </div>
  );
}
