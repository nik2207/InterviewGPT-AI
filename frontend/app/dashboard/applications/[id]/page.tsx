"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { PageHeader } from "@/components/ui/PageHeader";
import { getApiErrorMessage } from "@/lib/api/errors";
import {
  deleteApplication,
  fetchApplication,
  startApplicationPractice,
  updateApplication,
} from "@/lib/api/jobApplications";
import { fetchJobMatches } from "@/lib/api/jobMatch";
import { fetchResumes } from "@/lib/api/resumes";
import type { JobMatchListItem } from "@/types/jobMatch";
import {
  APPLICATION_STATUS_LABELS,
  APPLICATION_STATUS_ORDER,
  EMPLOYMENT_TYPE_LABELS,
  type ApplicationStatus,
  type EmploymentType,
  type InterviewDateEntry,
  type JobApplication,
} from "@/types/jobApplication";
import type { ResumeMetadata } from "@/types/resume";

export default function ApplicationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const appId = typeof params.id === "string" ? params.id : "";

  const [app, setApp] = useState<JobApplication | null>(null);
  const [resumes, setResumes] = useState<ResumeMetadata[]>([]);
  const [matches, setMatches] = useState<JobMatchListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newInterview, setNewInterview] = useState({
    label: "Interview",
    scheduled_at: "",
    notes: "",
  });

  const load = useCallback(async () => {
    if (!appId) return;
    setLoading(true);
    try {
      const detail = await fetchApplication(appId);
      setApp(detail);
    } catch (loadError) {
      setError(getApiErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [appId]);

  useEffect(() => {
    void load();
    fetchResumes()
      .then((data) => setResumes(data.resumes))
      .catch(() => undefined);
    fetchJobMatches()
      .then(setMatches)
      .catch(() => undefined);
  }, [load]);

  async function patch(fields: Partial<JobApplication>) {
    if (!app) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateApplication(app.id, fields);
      setApp(updated);
    } catch (patchError) {
      setError(getApiErrorMessage(patchError));
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveNotes(notes: string) {
    await patch({ notes });
  }

  async function handleAddInterview() {
    if (!app || !newInterview.scheduled_at) {
      setError("Pick a date and time for the interview.");
      return;
    }
    const entry: InterviewDateEntry = {
      id: crypto.randomUUID().replace(/-/g, "").slice(0, 12),
      label: newInterview.label.trim() || "Interview",
      scheduled_at: new Date(newInterview.scheduled_at).toISOString(),
      notes: newInterview.notes.trim(),
    };
    await patch({ interview_dates: [...app.interview_dates, entry] });
    setNewInterview({ label: "Interview", scheduled_at: "", notes: "" });
  }

  async function handlePractice() {
    if (!app) return;
    setSaving(true);
    try {
      const result = await startApplicationPractice(app.id, {
        resume_id: app.resume_id ?? undefined,
      });
      router.push(`/dashboard/interviews/${result.interview_session_id}`);
    } catch (practiceError) {
      setError(getApiErrorMessage(practiceError));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!app || !window.confirm("Delete this application?")) return;
    try {
      await deleteApplication(app.id);
      router.push("/dashboard/applications");
    } catch (deleteError) {
      setError(getApiErrorMessage(deleteError));
    }
  }

  if (loading) {
    return <p className="p-8 text-sm text-slate-500">Loading…</p>;
  }

  if (!app) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <p className="text-red-700">{error ?? "Application not found."}</p>
        <Link href="/dashboard/applications" className="mt-4 inline-block text-app-primary">
          Back to tracker
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-6 lg:px-8">
      <PageHeader
        title={`${app.company} — ${app.job_title}`}
        description="Edit details, link analysis, and start mock practice for this role."
      />

      <Link href="/dashboard/applications" className="text-sm text-app-primary hover:underline">
        ← All applications
      </Link>

      {error ? (
        <p className="rounded-control border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">
          {error}
        </p>
      ) : null}

      <section className="space-y-4 rounded-control border border-slate-200 bg-white p-5">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block sm:col-span-2">
            <span className="text-xs font-medium text-slate-600">Company</span>
            <input
              defaultValue={app.company}
              onBlur={(e) => {
                if (e.target.value.trim() !== app.company) {
                  void patch({ company: e.target.value.trim() });
                }
              }}
              className="mt-1 w-full rounded-control border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="block sm:col-span-2">
            <span className="text-xs font-medium text-slate-600">Job title</span>
            <input
              defaultValue={app.job_title}
              onBlur={(e) => {
                if (e.target.value.trim() !== app.job_title) {
                  void patch({ job_title: e.target.value.trim() });
                }
              }}
              className="mt-1 w-full rounded-control border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="block">
            <span className="text-xs font-medium text-slate-600">Status</span>
            <select
              value={app.status}
              onChange={(e) =>
                void patch({ status: e.target.value as ApplicationStatus })
              }
              className="mt-1 w-full rounded-control border border-slate-300 px-3 py-2 text-sm"
            >
              {APPLICATION_STATUS_ORDER.map((s) => (
                <option key={s} value={s}>
                  {APPLICATION_STATUS_LABELS[s]}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs font-medium text-slate-600">Employment type</span>
            <select
              value={app.employment_type}
              onChange={(e) =>
                void patch({ employment_type: e.target.value as EmploymentType })
              }
              className="mt-1 w-full rounded-control border border-slate-300 px-3 py-2 text-sm"
            >
              {Object.entries(EMPLOYMENT_TYPE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="block sm:col-span-2">
            <span className="text-xs font-medium text-slate-600">Job description</span>
            <textarea
              rows={6}
              defaultValue={app.job_description}
              onBlur={(e) => {
                if (e.target.value !== app.job_description) {
                  void patch({ job_description: e.target.value });
                }
              }}
              className="mt-1 w-full rounded-control border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
          {app.job_posting_url ? (
            <p className="sm:col-span-2 text-sm">
              <a
                href={app.job_posting_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-app-primary hover:underline"
              >
                View job posting
              </a>
            </p>
          ) : null}
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="text-xs font-medium text-slate-600">Resume</span>
          <select
            value={app.resume_id ?? ""}
            onChange={(e) =>
              void patch({ resume_id: e.target.value || null })
            }
            className="mt-1 w-full rounded-control border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">None</option>
            {resumes.map((r) => (
              <option key={r.id} value={r.id}>
                {r.original_filename}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="text-xs font-medium text-slate-600">Job match</span>
          <select
            value={app.job_match_id ?? ""}
            onChange={(e) =>
              void patch({ job_match_id: e.target.value || null })
            }
            className="mt-1 w-full rounded-control border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">None</option>
            {matches.map((m) => (
              <option key={m.id} value={m.id}>
                {m.job_title} ({Math.round(m.match_score)}%)
              </option>
            ))}
          </select>
        </label>
      </section>

      <div className="flex flex-wrap gap-3">
        {app.job_match_id ? (
          <Link
            href={`/dashboard/career/matches/${app.job_match_id}`}
            className="rounded-control border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50"
          >
            Open job match
          </Link>
        ) : null}
        <button
          type="button"
          disabled={saving}
          onClick={() => void handlePractice()}
          className="rounded-control bg-app-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Start mock interview
        </button>
        {app.interview_session_id ? (
          <Link
            href={`/dashboard/interviews/${app.interview_session_id}`}
            className="rounded-control border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50"
          >
            Last practice session
          </Link>
        ) : null}
      </div>

      <section className="rounded-control border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-slate-900">Interview dates</h2>
        <ul className="mt-2 space-y-2 text-sm text-slate-700">
          {app.interview_dates.map((row) => (
            <li key={row.id}>
              <strong>{row.label}</strong> —{" "}
              {new Date(row.scheduled_at).toLocaleString()}
              {row.notes ? ` (${row.notes})` : ""}
            </li>
          ))}
        </ul>
        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          <input
            placeholder="Label"
            value={newInterview.label}
            onChange={(e) =>
              setNewInterview((n) => ({ ...n, label: e.target.value }))
            }
            className="rounded-control border border-slate-300 px-3 py-2 text-sm"
          />
          <input
            type="datetime-local"
            value={newInterview.scheduled_at}
            onChange={(e) =>
              setNewInterview((n) => ({ ...n, scheduled_at: e.target.value }))
            }
            className="rounded-control border border-slate-300 px-3 py-2 text-sm"
          />
          <button
            type="button"
            onClick={() => void handleAddInterview()}
            className="rounded-control border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50"
          >
            Add date
          </button>
        </div>
      </section>

      <section className="rounded-control border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-slate-900">Notes</h2>
        <textarea
          rows={5}
          defaultValue={app.notes}
          onBlur={(e) => {
            if (e.target.value !== app.notes) {
              void handleSaveNotes(e.target.value);
            }
          }}
          className="mt-2 w-full rounded-control border border-slate-300 px-3 py-2 text-sm"
        />
        <label className="mt-3 block max-w-xs">
          <span className="text-xs font-medium text-slate-600">Follow-up date</span>
          <input
            type="date"
            value={app.follow_up_date ?? ""}
            onChange={(e) =>
              void patch({ follow_up_date: e.target.value || null })
            }
            className="mt-1 w-full rounded-control border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
      </section>

      <button
        type="button"
        onClick={() => void handleDelete()}
        className="text-sm text-red-600 hover:underline"
      >
        Delete application
      </button>
    </div>
  );
}
