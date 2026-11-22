"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/ui/PageHeader";
import { getApiErrorMessage } from "@/lib/api/errors";
import { createResumeBuilder, listResumeBuilders } from "@/lib/api/resumeBuilder";
import type { ResumeBuilderListItem } from "@/types/resumeBuilder";

export default function ResumeBuilderListPage() {
  const router = useRouter();
  const [items, setItems] = useState<ResumeBuilderListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listResumeBuilders()
      .then(setItems)
      .catch((cause: unknown) => setError(getApiErrorMessage(cause)))
      .finally(() => setLoading(false));
  }, []);

  async function handleCreate() {
    setCreating(true);
    setError(null);
    try {
      const doc = await createResumeBuilder({ title: "My resume" });
      router.push(`/dashboard/resumes/builder/${doc.id}`);
    } catch (cause: unknown) {
      setError(`Could not create resume: ${getApiErrorMessage(cause)}`);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        title="ATS resume builder"
        description="Create editable resumes separate from uploaded PDFs. No guaranteed ATS score — verify all content before applying."
      />
      <Link href="/dashboard/resumes" className="text-sm text-brand-700 hover:underline">
        ← Uploaded resumes & analysis
      </Link>

      {error ? (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}

      <button
        type="button"
        className="btn-primary"
        disabled={creating}
        onClick={handleCreate}
      >
        {creating ? "Creating…" : "New resume"}
      </button>

      {loading ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : (
        <ul className="app-card divide-y divide-slate-100">
          {items.length === 0 ? (
            <li className="p-4 text-sm text-slate-500">No builder resumes yet.</li>
          ) : (
            items.map((item) => (
              <li key={item.id} className="flex items-center justify-between p-4">
                <div>
                  <p className="font-medium text-slate-900">{item.title}</p>
                  <p className="text-xs text-slate-500">
                    {item.template} · {item.version_count} versions ·{" "}
                    {new Date(item.updated_at).toLocaleString()}
                  </p>
                </div>
                <Link
                  href={`/dashboard/resumes/builder/${item.id}`}
                  className="btn-secondary text-sm"
                >
                  Edit
                </Link>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
