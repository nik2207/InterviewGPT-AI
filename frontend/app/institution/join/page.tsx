"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { getApiErrorMessage } from "@/lib/api/errors";
import { acceptInstitutionInvitation } from "@/lib/api/institutions";

export default function InstitutionJoinPage() {
  const router = useRouter();
  const search = useSearchParams();
  const token = search.get("token");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setError("Missing invitation token.");
      return;
    }
    void acceptInstitutionInvitation(token)
      .then(() => router.replace("/institution"))
      .catch((e) => setError(getApiErrorMessage(e)));
  }, [token, router]);

  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      {error ? (
        <p className="text-sm text-red-700">{error}</p>
      ) : (
        <p className="text-sm text-slate-600">Accepting invitation…</p>
      )}
    </div>
  );
}
