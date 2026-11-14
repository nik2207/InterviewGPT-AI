"use client";

import { useEffect, useState } from "react";

import { PageHeader } from "@/components/ui/PageHeader";
import { getApiErrorMessage } from "@/lib/api/errors";
import {
  fetchGitHubAnalyses,
  fetchGitHubAnalysis,
  lookupGitHubProfile,
  runGitHubAnalyses,
} from "@/lib/api/githubAnalysis";
import type {
  GitHubAnalysisDetail,
  GitHubAnalysisListItem,
  GitHubProfileLookupResponse,
  GitHubPublicRepositorySummary,
} from "@/types/githubAnalysis";

export default function GitHubAnalyzerPage() {
  const [inputValue, setInputValue] = useState("");
  const [lookup, setLookup] = useState<GitHubProfileLookupResponse | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [results, setResults] = useState<GitHubAnalysisDetail[]>([]);
  const [history, setHistory] = useState<GitHubAnalysisListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGitHubAnalyses()
      .then(setHistory)
      .catch(() => {
        /* optional */
      });
  }, []);

  async function handleLookup() {
    setLoading(true);
    setError(null);
    setResults([]);
    try {
      const data = await lookupGitHubProfile(inputValue.trim());
      setLookup(data);
      setSelected(new Set());
    } catch (lookupError) {
      setLookup(null);
      setError(getApiErrorMessage(lookupError));
    } finally {
      setLoading(false);
    }
  }

  function toggleRepo(repo: GitHubPublicRepositorySummary) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(repo.full_name)) {
        next.delete(repo.full_name);
      } else {
        next.add(repo.full_name);
      }
      return next;
    });
  }

  async function handleAnalyze() {
    if (!lookup || selected.size === 0) {
      setError("Select at least one public repository.");
      return;
    }
    setAnalyzing(true);
    setError(null);
    try {
      const analyses = await runGitHubAnalyses(lookup.owner, [...selected]);
      setResults(analyses);
      setHistory(await fetchGitHubAnalyses());
    } catch (analyzeError) {
      setError(getApiErrorMessage(analyzeError));
    } finally {
      setAnalyzing(false);
    }
  }

  async function openHistoryItem(id: string) {
    try {
      const detail = await fetchGitHubAnalysis(id);
      setResults([detail]);
    } catch {
      setError("Unable to load saved analysis.");
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        title="GitHub profile analyzer"
        description="Inspect public repositories via the GitHub API and generate evidence-based interview prep. We never run repository code or guarantee authorship."
      />

      {error ? (
        <p className="rounded-control border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}

      <section className="app-card space-y-3 p-5">
        <label className="block text-sm font-medium text-app-ink">
          GitHub username or repository URL
          <input
            className="mt-1 w-full rounded-control border border-slate-200 px-3 py-2 text-sm"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="octocat or https://github.com/octocat/Hello-World"
          />
        </label>
        <button
          type="button"
          className="btn-primary"
          disabled={loading || !inputValue.trim()}
          onClick={handleLookup}
        >
          {loading ? "Looking up…" : "Find public repositories"}
        </button>
      </section>

      {lookup ? (
        <section className="app-card p-5">
          <h2 className="text-lg font-semibold text-app-ink">
            {lookup.profile_name ?? lookup.owner}
          </h2>
          <p className="text-sm text-app-muted">{lookup.bio}</p>
          <a
            href={lookup.profile_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-app-primary hover:underline"
          >
            View profile
          </a>
          <p className="mt-2 text-xs text-app-muted">{lookup.disclaimer}</p>
          {lookup.rate_limit_remaining != null ? (
            <p className="text-xs text-app-muted">
              GitHub API rate limit remaining: {lookup.rate_limit_remaining}
            </p>
          ) : null}

          <ul className="mt-4 max-h-64 space-y-2 overflow-y-auto">
            {lookup.repositories.map((repo) => (
              <li key={repo.full_name} className="flex items-start gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={selected.has(repo.full_name)}
                  onChange={() => toggleRepo(repo)}
                  aria-label={`Select ${repo.full_name}`}
                />
                <div>
                  <p className="font-medium">{repo.full_name}</p>
                  <p className="text-xs text-app-muted">
                    {repo.primary_language ?? "Unknown language"} · {repo.stars} stars
                    {repo.is_fork ? " · fork" : ""}
                  </p>
                  <p className="text-xs text-app-muted">{repo.description}</p>
                </div>
              </li>
            ))}
          </ul>

          <button
            type="button"
            className="btn-primary mt-4"
            disabled={analyzing || selected.size === 0}
            onClick={handleAnalyze}
          >
            {analyzing ? "Analyzing…" : `Analyze ${selected.size} selected`}
          </button>
        </section>
      ) : null}

      {results.map((item) => (
        <article key={item.id} className="app-card space-y-4 p-5">
          <header>
            <h3 className="text-lg font-semibold">{item.repo_full_name}</h3>
            <p className="text-xs text-app-muted">{item.disclaimer}</p>
            {item.status === "failed" ? (
              <p className="text-sm text-red-600">{item.error_message}</p>
            ) : null}
          </header>

          <div className="text-sm">
            <p className="font-medium">What we inspected</p>
            <ul className="mt-1 list-disc pl-5 text-app-muted">
              {item.inspection.sources_inspected.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
            <p className="mt-2 font-medium">Not inspected</p>
            <ul className="list-disc pl-5 text-app-muted">
              {item.inspection.not_inspected.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </div>

          {item.result ? (
            <div className="space-y-3 text-sm">
              <p>{item.result.project_description}</p>
              <p>
                <span className="font-medium">Languages: </span>
                {item.result.main_languages.join(", ") || "—"}
              </p>
              <p>
                <span className="font-medium">Frameworks / libraries (evidence-based): </span>
                {item.result.frameworks_and_libraries.join(", ") || "—"}
              </p>
              <p>{item.result.structure_overview}</p>
              <p className="font-medium text-amber-800">{item.result.authorship_caveat}</p>

              <div>
                <h4 className="font-semibold">Interview questions</h4>
                <ul className="mt-2 space-y-2">
                  {item.result.interview_questions.map((q) => (
                    <li key={q.question} className="rounded border border-slate-100 p-2">
                      <p className="text-xs uppercase text-app-primary">{q.category}</p>
                      <p className="font-medium">{q.question}</p>
                      <p className="text-xs text-app-muted">Basis: {q.evidence_basis}</p>
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <h4 className="font-semibold">Explain in an interview</h4>
                <ul className="list-disc pl-5">
                  {item.result.project_explanation_prep.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </div>

              <p className="text-xs text-app-muted">
                Unknowns: {item.result.unknowns.join("; ") || "—"}
              </p>
            </div>
          ) : null}
        </article>
      ))}

      {history.length > 0 ? (
        <section className="app-card p-5">
          <h3 className="text-sm font-semibold">Analysis history</h3>
          <ul className="mt-2 divide-y divide-slate-100 text-sm">
            {history.map((item) => (
              <li key={item.id} className="flex items-center justify-between py-2">
                <span>
                  {item.repo_full_name} · {item.status}
                </span>
                <button
                  type="button"
                  className="btn-secondary text-xs"
                  onClick={() => openHistoryItem(item.id)}
                >
                  Open
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
