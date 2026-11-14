"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { PageHeader } from "@/components/ui/PageHeader";
import { getApiErrorMessage } from "@/lib/api/errors";
import {
  createApplication,
  fetchApplicationStats,
  fetchApplications,
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
  type JobApplication,
  type JobApplicationStats,
} from "@/types/jobApplication";
import type { ResumeMetadata } from "@/types/resume";

type ViewMode = "kanban" | "table";

const emptyForm = {
  company: "",
  job_title: "",
  job_description: "",
  job_posting_url: "",
  location: "",
  employment_type: "full_time" as EmploymentType,
  application_date: "",
  status: "interested" as ApplicationStatus,
  resume_id: "",
  job_match_id: "",
  notes: "",
  follow_up_date: "",
};

export default function ApplicationsPage() {
  const router = useRouter();
  const [view, setView] = useState<ViewMode>("kanban");
  const [items, setItems] = useState<JobApplication[]>([]);
  const [stats, setStats] = useState<JobApplicationStats | null>(null);
  const [disclaimer, setDisclaimer] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [resumes, setResumes] = useState<ResumeMetadata[]>([]);
  const [matches, setMatches] = useState<JobMatchListItem[]>([]);
  const [practiceId, setPracticeId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [list, stat] = await Promise.all([
        fetchApplications({
          q: search.trim() || undefined,
          status: statusFilter || undefined,
          page_size: 100,
          sort_by: "updated_at",
          sort_dir: -1,
        }),
        fetchApplicationStats(),
      ]);
      setItems(list.items);
      setDisclaimer(list.disclaimer);
      setStats(stat);
    } catch (loadError) {
      setError(getApiErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void load();
    }, 250);
    return () => window.clearTimeout(handle);
  }, [load]);

  useEffect(() => {
    fetchResumes()
      .then((data) => setResumes(data.resumes))
      .catch(() => undefined);
    fetchJobMatches()
      .then(setMatches)
      .catch(() => undefined);
  }, []);

  const byStatus = useMemo(() => {
    const map = APPLICATION_STATUS_ORDER.reduce(
      (acc, status) => {
        acc[status] = [];
        return acc;
      },
      {} as Record<ApplicationStatus, JobApplication[]>
    );
    for (const app of items) {
      map[app.status].push(app);
    }
    return map;
  }, [items]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.company.trim() || !form.job_title.trim()) {
      setError("Company and job title are required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createApplication({
        company: form.company.trim(),
        job_title: form.job_title.trim(),
        job_description: form.job_description.trim(),
        job_posting_url: form.job_posting_url.trim() || null,
        location: form.location.trim(),
        employment_type: form.employment_type,
        application_date: form.application_date || null,
        status: form.status,
        resume_id: form.resume_id || null,
        job_match_id: form.job_match_id || null,
        notes: form.notes.trim(),
        follow_up_date: form.follow_up_date || null,
      });
      setShowForm(false);
      setForm(emptyForm);
      await load();
    } catch (saveError) {
      setError(getApiErrorMessage(saveError));
    } finally {
      setSaving(false);
    }
  }

  async function handleStatusChange(app: JobApplication, status: ApplicationStatus) {
    try {
      await updateApplication(app.id, { status });
      await load();
    } catch (updateError) {
      setError(getApiErrorMessage(updateError));
    }
  }

  async function handleQuickPractice(app: JobApplication) {
    setPracticeId(app.id);
    setError(null);
    try {
      const result = await startApplicationPractice(app.id, {
        resume_id: app.resume_id ?? undefined,
      });
      router.push(`/dashboard/interviews/${result.interview_session_id}`);
    } catch (practiceError) {
      setError(getApiErrorMessage(practiceError));
    } finally {
      setPracticeId(null);
    }
  }

  function ApplicationCard({ app }: { app: JobApplication }) {
    return (
      <article className="rounded-control border border-slate-200 bg-white p-3 shadow-sm">
        <div className="flex items-start justify-between gap-2">
          <button
            type="button"
            className="text-left"
            onClick={() => router.push(`/dashboard/applications/${app.id}`)}
          >
            <p className="text-sm font-semibold text-slate-900">{app.company}</p>
            <p className="text-xs text-slate-600">{app.job_title}</p>
          </button>
          <select
            className="max-w-[9rem] rounded border border-slate-200 px-1 py-0.5 text-[10px]"
            value={app.status}
            onChange={(e) =>
              handleStatusChange(app, e.target.value as ApplicationStatus)
            }
            aria-label={`Status for ${app.company}`}
          >
            {APPLICATION_STATUS_ORDER.map((s) => (
              <option key={s} value={s}>
                {APPLICATION_STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </div>
        {app.location ? (
          <p className="mt-1 text-[11px] text-slate-500">{app.location}</p>
        ) : null}
        <div className="mt-2 flex flex-wrap gap-2">
          {app.job_match_id ? (
            <Link
              href={`/dashboard/career/matches/${app.job_match_id}`}
              className="text-[11px] text-app-primary hover:underline"
            >
              Job match
            </Link>
          ) : null}
          <button
            type="button"
            disabled={practiceId === app.id}
            onClick={() => handleQuickPractice(app)}
            className="text-[11px] text-app-primary hover:underline disabled:opacity-50"
          >
            Practice interview
          </button>
        </div>
      </article>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 lg:px-8">
      <PageHeader
        title="Job applications"
        description="Track applications, link resumes and job-match analysis, and practice for each role."
      />

      {disclaimer ? (
        <p className="rounded-control border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900">
          {disclaimer}
        </p>
      ) : null}

      {error ? (
        <p className="rounded-control border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">
          {error}
        </p>
      ) : null}

      {stats ? (
        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile label="Total" value={stats.total} />
          <StatTile
            label="Active pipeline"
            value={
              (stats.by_status.interested ?? 0) +
              (stats.by_status.applied ?? 0) +
              (stats.by_status.assessment ?? 0) +
              (stats.by_status.interview_scheduled ?? 0)
            }
          />
          <StatTile
            label="Offers"
            value={stats.by_status.offer_received ?? 0}
          />
          <StatTile label="Interviews soon" value={stats.upcoming_interviews.length} />
        </section>
      ) : null}

      {stats && (stats.upcoming_interviews.length > 0 || stats.upcoming_follow_ups.length > 0) ? (
        <section className="grid gap-4 lg:grid-cols-2">
          {stats.upcoming_interviews.length > 0 ? (
            <div className="rounded-control border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold text-slate-900">Upcoming interviews</h2>
              <ul className="mt-2 space-y-2 text-sm text-slate-700">
                {stats.upcoming_interviews.map((row) => (
                  <li key={`${row.application_id}-${row.scheduled_at}`}>
                    <Link
                      href={`/dashboard/applications/${row.application_id}`}
                      className="text-app-primary hover:underline"
                    >
                      {row.company} — {row.job_title}
                    </Link>
                    <span className="ml-2 text-xs text-slate-500">
                      {new Date(row.scheduled_at).toLocaleString()}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {stats.upcoming_follow_ups.length > 0 ? (
            <div className="rounded-control border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold text-slate-900">Follow-up dates</h2>
              <ul className="mt-2 space-y-2 text-sm text-slate-700">
                {stats.upcoming_follow_ups.map((row) => (
                  <li key={`${row.application_id}-${row.follow_up_date}`}>
                    <Link
                      href={`/dashboard/applications/${row.application_id}`}
                      className="text-app-primary hover:underline"
                    >
                      {row.company} — {row.job_title}
                    </Link>
                    <span className="ml-2 text-xs text-slate-500">
                      {row.follow_up_date}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <input
          type="search"
          placeholder="Search company or title…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="min-w-[200px] flex-1 rounded-control border border-slate-300 px-3 py-2 text-sm"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-control border border-slate-300 px-3 py-2 text-sm"
          aria-label="Filter by status"
        >
          <option value="">All statuses</option>
          {APPLICATION_STATUS_ORDER.map((s) => (
            <option key={s} value={s}>
              {APPLICATION_STATUS_LABELS[s]}
            </option>
          ))}
        </select>
        <div className="flex rounded-control border border-slate-300 p-0.5">
          <button
            type="button"
            className={`rounded px-3 py-1.5 text-sm ${view === "kanban" ? "bg-app-primary text-white" : "text-slate-600"}`}
            onClick={() => setView("kanban")}
          >
            Kanban
          </button>
          <button
            type="button"
            className={`rounded px-3 py-1.5 text-sm ${view === "table" ? "bg-app-primary text-white" : "text-slate-600"}`}
            onClick={() => setView("table")}
          >
            Table
          </button>
        </div>
        <button
          type="button"
          onClick={() => setShowForm(true)}
          className="rounded-control bg-app-primary px-4 py-2 text-sm font-medium text-white hover:opacity-90"
        >
          Add application
        </button>
      </div>

      {loading ? (
        <p className="text-sm text-slate-500">Loading applications…</p>
      ) : view === "kanban" ? (
        <div className="flex gap-3 overflow-x-auto pb-2">
          {APPLICATION_STATUS_ORDER.map((status) => (
            <div
              key={status}
              className="min-w-[240px] flex-1 rounded-control border border-slate-200 bg-slate-50 p-2"
            >
              <h3 className="mb-2 px-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
                {APPLICATION_STATUS_LABELS[status]} ({byStatus[status].length})
              </h3>
              <div className="space-y-2">
                {byStatus[status].map((app) => (
                  <ApplicationCard key={app.id} app={app} />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-control border border-slate-200 bg-white">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-600">
              <tr>
                <th className="px-4 py-3">Company</th>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Applied</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((app) => (
                <tr key={app.id} className="border-b border-slate-100">
                  <td className="px-4 py-3 font-medium">{app.company}</td>
                  <td className="px-4 py-3">{app.job_title}</td>
                  <td className="px-4 py-3">
                    <select
                      className="rounded border border-slate-200 px-2 py-1 text-xs"
                      value={app.status}
                      onChange={(e) =>
                        handleStatusChange(app, e.target.value as ApplicationStatus)
                      }
                    >
                      {APPLICATION_STATUS_ORDER.map((s) => (
                        <option key={s} value={s}>
                          {APPLICATION_STATUS_LABELS[s]}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {app.application_date ?? "—"}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/dashboard/applications/${app.id}`}
                      className="text-app-primary hover:underline"
                    >
                      Details
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {items.length === 0 ? (
            <p className="p-6 text-center text-sm text-slate-500">
              No applications yet. Add your first role above.
            </p>
          ) : null}
        </div>
      )}

      {showForm ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <form
            onSubmit={handleCreate}
            className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-control bg-white p-6 shadow-xl"
          >
            <h2 className="text-lg font-semibold text-slate-900">New application</h2>
            <ApplicationFormFields
              form={form}
              setForm={setForm}
              resumes={resumes}
              matches={matches}
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded-control border border-slate-300 px-4 py-2 text-sm"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="rounded-control bg-app-primary px-4 py-2 text-sm text-white disabled:opacity-50"
              >
                {saving ? "Saving…" : "Save"}
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </div>
  );
}

function StatTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-control border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
    </div>
  );
}

function ApplicationFormFields({
  form,
  setForm,
  resumes,
  matches,
}: {
  form: typeof emptyForm;
  setForm: React.Dispatch<React.SetStateAction<typeof emptyForm>>;
  resumes: ResumeMetadata[];
  matches: JobMatchListItem[];
}) {
  return (
    <div className="mt-4 grid gap-3 sm:grid-cols-2">
      <label className="block sm:col-span-2">
        <span className="text-xs font-medium text-slate-600">Company *</span>
        <input
          required
          value={form.company}
          onChange={(e) => setForm((f) => ({ ...f, company: e.target.value }))}
          className="mt-1 w-full rounded-control border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
      <label className="block sm:col-span-2">
        <span className="text-xs font-medium text-slate-600">Job title *</span>
        <input
          required
          value={form.job_title}
          onChange={(e) => setForm((f) => ({ ...f, job_title: e.target.value }))}
          className="mt-1 w-full rounded-control border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
      <label className="block sm:col-span-2">
        <span className="text-xs font-medium text-slate-600">Job description</span>
        <textarea
          rows={4}
          value={form.job_description}
          onChange={(e) => setForm((f) => ({ ...f, job_description: e.target.value }))}
          className="mt-1 w-full rounded-control border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
      <label className="block sm:col-span-2">
        <span className="text-xs font-medium text-slate-600">Posting URL</span>
        <input
          type="url"
          value={form.job_posting_url}
          onChange={(e) => setForm((f) => ({ ...f, job_posting_url: e.target.value }))}
          className="mt-1 w-full rounded-control border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
      <label className="block">
        <span className="text-xs font-medium text-slate-600">Location</span>
        <input
          value={form.location}
          onChange={(e) => setForm((f) => ({ ...f, location: e.target.value }))}
          className="mt-1 w-full rounded-control border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
      <label className="block">
        <span className="text-xs font-medium text-slate-600">Employment type</span>
        <select
          value={form.employment_type}
          onChange={(e) =>
            setForm((f) => ({
              ...f,
              employment_type: e.target.value as EmploymentType,
            }))
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
      <label className="block">
        <span className="text-xs font-medium text-slate-600">Application date</span>
        <input
          type="date"
          value={form.application_date}
          onChange={(e) => setForm((f) => ({ ...f, application_date: e.target.value }))}
          className="mt-1 w-full rounded-control border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
      <label className="block">
        <span className="text-xs font-medium text-slate-600">Follow-up date</span>
        <input
          type="date"
          value={form.follow_up_date}
          onChange={(e) => setForm((f) => ({ ...f, follow_up_date: e.target.value }))}
          className="mt-1 w-full rounded-control border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
      <label className="block">
        <span className="text-xs font-medium text-slate-600">Status</span>
        <select
          value={form.status}
          onChange={(e) =>
            setForm((f) => ({ ...f, status: e.target.value as ApplicationStatus }))
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
        <span className="text-xs font-medium text-slate-600">Resume</span>
        <select
          value={form.resume_id}
          onChange={(e) => setForm((f) => ({ ...f, resume_id: e.target.value }))}
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
      <label className="block sm:col-span-2">
        <span className="text-xs font-medium text-slate-600">Linked job match</span>
        <select
          value={form.job_match_id}
          onChange={(e) => setForm((f) => ({ ...f, job_match_id: e.target.value }))}
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
      <label className="block sm:col-span-2">
        <span className="text-xs font-medium text-slate-600">Notes</span>
        <textarea
          rows={3}
          value={form.notes}
          onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
          className="mt-1 w-full rounded-control border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
    </div>
  );
}
