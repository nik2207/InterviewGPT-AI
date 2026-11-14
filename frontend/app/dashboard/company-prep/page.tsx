"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { PageHeader } from "@/components/ui/PageHeader";
import { getApiErrorMessage } from "@/lib/api/errors";
import {
  createCompanyPreparation,
  fetchCompanyPreparations,
  searchCompanies,
  startCompanyPrepInterview,
  updateCompanyPrepChecklist,
} from "@/lib/api/companyPrep";
import type {
  CompanyCatalogueEntry,
  CompanyPrepDetail,
  CompanyPrepListItem,
  CompanyPrepQuestion,
  ExperienceLevel,
  PrepCategory,
} from "@/types/companyPrep";
import {
  PREP_CATEGORY_LABELS,
  SOURCE_TYPE_LABELS,
} from "@/types/companyPrep";

const ALL_CATEGORIES: PrepCategory[] = [
  "technical",
  "coding",
  "behavioural",
  "hr",
];

export default function CompanyPrepPage() {
  const router = useRouter();
  const [history, setHistory] = useState<CompanyPrepListItem[]>([]);
  const [catalogueDisclaimer, setCatalogueDisclaimer] = useState("");
  const [search, setSearch] = useState("");
  const [companies, setCompanies] = useState<CompanyCatalogueEntry[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<CompanyCatalogueEntry | null>(null);
  const [jobRole, setJobRole] = useState("Software Engineer");
  const [experienceLevel, setExperienceLevel] = useState<ExperienceLevel>("mid");
  const [categories, setCategories] = useState<PrepCategory[]>([
    "technical",
    "coding",
    "behavioural",
  ]);
  const [userNotes, setUserNotes] = useState("");
  const [prep, setPrep] = useState<CompanyPrepDetail | null>(null);
  const [questionFilter, setQuestionFilter] = useState<PrepCategory | "all">("all");
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [startingInterview, setStartingInterview] = useState(false);

  const loadHistory = useCallback(async () => {
    try {
      const items = await fetchCompanyPreparations();
      setHistory(items);
    } catch {
      /* non-blocking */
    }
  }, []);

  useEffect(() => {
    loadHistory();
    searchCompanies()
      .then((data) => {
        setCompanies(data.companies);
        setCatalogueDisclaimer(data.disclaimer);
      })
      .catch(() => setError("Unable to load company catalogue."));
  }, [loadHistory]);

  useEffect(() => {
    const handle = window.setTimeout(async () => {
      setSearching(true);
      try {
        const data = await searchCompanies(search.trim() || undefined);
        setCompanies(data.companies);
        setCatalogueDisclaimer(data.disclaimer);
      } catch {
        setError("Company search failed.");
      } finally {
        setSearching(false);
      }
    }, 300);
    return () => window.clearTimeout(handle);
  }, [search]);

  const filteredQuestions = useMemo(() => {
    if (!prep) return [];
    if (questionFilter === "all") return prep.questions;
    return prep.questions.filter((q) => q.prep_category === questionFilter);
  }, [prep, questionFilter]);

  function toggleCategory(cat: PrepCategory) {
    setCategories((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    );
  }

  async function handleGenerate() {
    if (!selectedCompany) {
      setError("Select a company first.");
      return;
    }
    if (categories.length === 0) {
      setError("Select at least one interview category.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const detail = await createCompanyPreparation({
        company_id: selectedCompany.id,
        job_role: jobRole.trim(),
        experience_level: experienceLevel,
        categories,
        user_notes: userNotes.trim() || undefined,
      });
      setPrep(detail);
      await loadHistory();
    } catch (genError) {
      setError(getApiErrorMessage(genError));
    } finally {
      setLoading(false);
    }
  }

  async function toggleChecklistItem(itemId: string) {
    if (!prep) return;
    const next = prep.checklist.map((item) =>
      item.id === itemId ? { ...item, completed: !item.completed } : item
    );
    try {
      const updated = await updateCompanyPrepChecklist(prep.id, next);
      setPrep(updated);
    } catch {
      setError("Could not update checklist.");
    }
  }

  async function handleStartInterview() {
    if (!prep) return;
    setStartingInterview(true);
    setError(null);
    try {
      const result = await startCompanyPrepInterview(prep.id, {
        question_count: Math.min(8, prep.questions.length),
      });
      router.push(`/dashboard/interviews/${result.interview_session_id}`);
    } catch (startError) {
      setError(getApiErrorMessage(startError));
    } finally {
      setStartingInterview(false);
    }
  }

  function loadPastPrep(prepId: string) {
    setLoading(true);
    import("@/lib/api/companyPrep")
      .then(({ fetchCompanyPreparation }) => fetchCompanyPreparation(prepId))
      .then((detail) => {
        setPrep(detail);
        setSelectedCompany(detail.company);
        setJobRole(detail.job_role);
        setExperienceLevel(detail.experience_level);
        setCategories(detail.categories);
      })
      .catch(() => setError("Unable to load saved preparation."))
      .finally(() => setLoading(false));
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        title="Company interview prep"
        description="Search a company, build a practice pack, and launch a mock interview. Practice questions are AI-generated — not leaked or guaranteed real questions."
      />

      {error ? (
        <p className="rounded-control border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}

      <p className="text-xs text-app-muted">{catalogueDisclaimer}</p>

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="app-card space-y-4 p-5 lg:col-span-1">
          <h2 className="text-sm font-semibold text-app-ink">1. Company</h2>
          <input
            type="search"
            className="w-full rounded-control border border-slate-200 px-3 py-2 text-sm"
            placeholder="Search companies…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search companies"
          />
          {searching ? (
            <p className="text-xs text-app-muted">Searching…</p>
          ) : (
            <ul className="max-h-48 space-y-1 overflow-y-auto">
              {companies.map((company) => (
                <li key={company.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedCompany(company)}
                    className={`w-full rounded-control px-2 py-2 text-left text-sm ${
                      selectedCompany?.id === company.id
                        ? "bg-app-primary-soft text-app-primary"
                        : "hover:bg-slate-50"
                    }`}
                  >
                    <span className="font-medium">{company.name}</span>
                    <span className="block text-xs text-app-muted">{company.industry}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {selectedCompany ? (
            <div className="rounded-control border border-slate-100 bg-slate-50 p-3 text-sm">
              <p className="font-medium text-app-ink">{selectedCompany.name}</p>
              <p className="mt-1 text-xs text-app-muted">{selectedCompany.public_profile_summary}</p>
              {selectedCompany.verified_public_sources.length > 0 ? (
                <ul className="mt-2 text-xs">
                  {selectedCompany.verified_public_sources.map((src) => (
                    <li key={src.url}>
                      <a
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-app-primary hover:underline"
                      >
                        {src.label} (public)
                      </a>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}

          <h2 className="text-sm font-semibold text-app-ink">2. Role &amp; level</h2>
          <label className="block text-xs font-medium text-app-muted">
            Job role
            <input
              className="mt-1 w-full rounded-control border border-slate-200 px-3 py-2 text-sm"
              value={jobRole}
              onChange={(e) => setJobRole(e.target.value)}
            />
          </label>
          <label className="block text-xs font-medium text-app-muted">
            Experience
            <select
              className="mt-1 w-full rounded-control border border-slate-200 px-3 py-2 text-sm"
              value={experienceLevel}
              onChange={(e) => setExperienceLevel(e.target.value as ExperienceLevel)}
            >
              <option value="junior">Junior</option>
              <option value="mid">Mid-level</option>
              <option value="senior">Senior</option>
            </select>
          </label>

          <h2 className="text-sm font-semibold text-app-ink">3. Categories</h2>
          <div className="flex flex-wrap gap-2">
            {ALL_CATEGORIES.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => toggleCategory(cat)}
                className={
                  categories.includes(cat)
                    ? "rounded-full bg-app-primary px-3 py-1 text-xs text-white"
                    : "rounded-full border border-slate-200 px-3 py-1 text-xs text-app-muted"
                }
              >
                {PREP_CATEGORY_LABELS[cat]}
              </button>
            ))}
          </div>

          <label className="block text-xs font-medium text-app-muted">
            Your notes (optional, user-provided context)
            <textarea
              className="mt-1 w-full rounded-control border border-slate-200 px-3 py-2 text-sm"
              rows={3}
              value={userNotes}
              onChange={(e) => setUserNotes(e.target.value)}
              placeholder="Topics you want emphasised in practice…"
            />
          </label>

          <button
            type="button"
            className="btn-primary w-full"
            disabled={loading || !selectedCompany}
            onClick={handleGenerate}
          >
            {loading ? "Generating practice pack…" : "Generate practice pack"}
          </button>
        </section>

        <section className="space-y-4 lg:col-span-2">
          {prep ? (
            <>
              <div className="app-card p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold text-app-ink">
                      {prep.company.name} · {prep.job_role}
                    </h2>
                    <p className="text-xs text-app-muted">{prep.disclaimer}</p>
                  </div>
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={startingInterview}
                    onClick={handleStartInterview}
                  >
                    {startingInterview ? "Starting…" : "Start mock interview"}
                  </button>
                </div>
                {prep.interview_session_id ? (
                  <p className="mt-2 text-sm">
                    <Link
                      href={`/dashboard/interviews/${prep.interview_session_id}`}
                      className="text-app-primary hover:underline"
                    >
                      Resume linked mock interview
                    </Link>
                  </p>
                ) : null}
              </div>

              <div className="app-card p-5">
                <h3 className="text-sm font-semibold text-app-ink">Preparation checklist</h3>
                <ul className="mt-3 space-y-2">
                  {prep.checklist.map((item) => (
                    <li key={item.id} className="flex items-start gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={item.completed}
                        onChange={() => toggleChecklistItem(item.id)}
                        className="mt-1"
                        aria-label={item.label}
                      />
                      <div className="flex-1">
                        <p className={item.completed ? "text-app-muted line-through" : "text-app-ink"}>
                          {item.label}
                        </p>
                        <p className="text-xs text-app-muted">
                          {SOURCE_TYPE_LABELS[item.source_type]} · {item.source_label}
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="app-card p-5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-sm font-semibold text-app-ink">Practice questions</h3>
                  <select
                    className="rounded-control border border-slate-200 px-2 py-1 text-xs"
                    value={questionFilter}
                    onChange={(e) =>
                      setQuestionFilter(e.target.value as PrepCategory | "all")
                    }
                    aria-label="Filter questions"
                  >
                    <option value="all">All categories</option>
                    {ALL_CATEGORIES.map((cat) => (
                      <option key={cat} value={cat}>
                        {PREP_CATEGORY_LABELS[cat]}
                      </option>
                    ))}
                  </select>
                </div>
                <ul className="mt-4 space-y-3">
                  {filteredQuestions.map((q: CompanyPrepQuestion) => (
                    <li
                      key={q.id}
                      className="rounded-control border border-slate-100 p-3 text-sm"
                    >
                      <p className="font-medium text-app-ink">{q.question}</p>
                      <p className="mt-1 text-xs text-app-muted">
                        {PREP_CATEGORY_LABELS[q.prep_category]} · {q.difficulty} ·{" "}
                        <span
                          className={
                            q.source_type === "ai_generated_practice"
                              ? "text-amber-800"
                              : "text-emerald-800"
                          }
                        >
                          {SOURCE_TYPE_LABELS[q.source_type]}
                        </span>
                      </p>
                      <p className="mt-1 text-xs text-app-muted">{q.disclaimer}</p>
                    </li>
                  ))}
                </ul>
              </div>

              {selectedCompany && selectedCompany.prep_material.length > 0 ? (
                <div className="app-card p-5">
                  <h3 className="text-sm font-semibold text-app-ink">Available public material</h3>
                  <ul className="mt-2 space-y-2 text-sm">
                    {selectedCompany.prep_material.map((m) => (
                      <li key={m.title} className="border-t border-slate-100 pt-2">
                        <p className="font-medium">{m.title}</p>
                        <p className="text-xs text-app-muted">{m.summary}</p>
                        {m.source_url ? (
                          <a
                            href={m.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-app-primary hover:underline"
                          >
                            Public source
                          </a>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </>
          ) : (
            <button
              type="button"
              className="app-card block w-full p-8 text-center text-sm text-app-muted hover:border-app-primary/30"
              onClick={() => selectedCompany && handleGenerate()}
              disabled={!selectedCompany}
            >
              Select a company and generate a practice pack to see questions and checklist here.
            </button>
          )}

          {history.length > 0 ? (
            <div className="app-card p-5">
              <h3 className="text-sm font-semibold text-app-ink">Saved preparations</h3>
              <ul className="mt-3 divide-y divide-slate-100">
                {history.map((item) => (
                  <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
                    <div>
                      <p className="font-medium">
                        {item.company_name} · {item.job_role}
                      </p>
                      <p className="text-xs text-app-muted">
                        {item.question_count} questions ·{" "}
                        {new Date(item.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <button
                      type="button"
                      className="btn-secondary text-xs"
                      onClick={() => loadPastPrep(item.id)}
                    >
                      Open
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
