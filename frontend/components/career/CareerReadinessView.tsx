"use client";

import { ScoreTrendChart } from "@/components/dashboard/ScoreTrendChart";
import type { CareerReadinessReport } from "@/types/careerReadiness";

interface CareerReadinessViewProps {
  report: CareerReadinessReport;
  onDownloadPdf: () => void;
  downloading: boolean;
}

function ScoreBar({ label, section }: { label: string; section: { score: number | null; status: string; detail: string } }) {
  const width =
    section.status === "available" && section.score !== null
      ? `${section.score}%`
      : "0%";
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="font-medium text-app-ink">{label}</span>
        <span className="text-app-muted">
          {section.status === "available" && section.score !== null
            ? `${section.score}/100`
            : "Not enough practice data"}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-app-border">
        <div className="h-full bg-app-primary transition-all" style={{ width }} />
      </div>
      <p className="text-xs text-app-muted">{section.detail}</p>
    </div>
  );
}

export function CareerReadinessView({
  report,
  onDownloadPdf,
  downloading,
}: CareerReadinessViewProps) {
  const trendPoints = report.interview_performance_trends
    .filter((p) => p.overall_score !== null)
    .slice()
    .reverse()
    .map((p) => ({
      label: new Date(p.completed_at).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      }),
      score: p.overall_score ?? 0,
    }));

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-app-ink">{report.target_role}</h2>
          <p className="mt-1 text-sm text-app-muted">
            Generated {new Date(report.generated_at).toLocaleString()} ·{" "}
            {report.data_coverage.summary}
          </p>
        </div>
        <button
          type="button"
          className="btn-primary"
          disabled={downloading}
          onClick={onDownloadPdf}
        >
          {downloading ? "Preparing PDF…" : "Download PDF"}
        </button>
      </header>

      <section className="app-card p-6">
        <h3 className="text-sm font-semibold uppercase text-app-muted">
          Overall readiness
        </h3>
        {report.overall_readiness.status === "available" &&
        report.overall_readiness.score !== null ? (
          <p className="mt-2 text-4xl font-semibold text-app-primary">
            {report.overall_readiness.score}
            <span className="text-lg text-app-muted">/100</span>
          </p>
        ) : (
          <p className="mt-2 text-lg text-amber-800">
            {report.overall_readiness.message}
          </p>
        )}
        <p className="mt-2 text-xs text-app-muted">{report.scoring_rules}</p>
      </section>

      <section className="app-card grid gap-4 p-6 md:grid-cols-2">
        <ScoreBar label="Resume–job alignment" section={report.resume_job_alignment} />
        <ScoreBar label="Technical knowledge" section={report.technical_knowledge} />
        <ScoreBar label="Answer relevance" section={report.answer_relevance} />
        <ScoreBar label="Answer completeness" section={report.answer_completeness} />
        <ScoreBar label="Answer structure" section={report.answer_structure} />
      </section>

      <section className="app-card p-6">
        <h3 className="text-sm font-semibold text-app-ink">Communication indicators</h3>
        {report.communication_indicators.status === "available" ? (
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-app-muted">Speech answers</dt>
              <dd className="font-medium">{report.communication_indicators.speech_answer_count}</dd>
            </div>
            <div>
              <dt className="text-app-muted">Avg words/min</dt>
              <dd className="font-medium">
                {report.communication_indicators.average_words_per_minute ?? "—"}
              </dd>
            </div>
            <div>
              <dt className="text-app-muted">Avg filler words</dt>
              <dd className="font-medium">
                {report.communication_indicators.average_filler_words ?? "—"}
              </dd>
            </div>
          </dl>
        ) : (
          <p className="mt-2 text-sm text-app-muted">
            {report.communication_indicators.detail}
          </p>
        )}
        <p className="mt-2 text-xs text-app-muted">
          {report.communication_indicators.disclaimer}
        </p>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="app-card p-6">
          <h3 className="text-sm font-semibold text-app-ink">Strongest skills</h3>
          {report.strongest_skills.length > 0 ? (
            <ul className="mt-3 list-disc pl-5 text-sm text-app-ink">
              {report.strongest_skills.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-app-muted">No skill evidence yet.</p>
          )}
        </section>
        <section className="app-card p-6">
          <h3 className="text-sm font-semibold text-app-ink">Skills to improve</h3>
          {report.skills_requiring_improvement.length > 0 ? (
            <ul className="mt-3 list-disc pl-5 text-sm text-app-ink">
              {report.skills_requiring_improvement.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-app-muted">No gaps identified yet.</p>
          )}
        </section>
      </div>

      <section className="app-card p-6">
        <h3 className="text-sm font-semibold text-app-ink">Interview performance trend</h3>
        <ScoreTrendChart points={trendPoints} />
      </section>

      <section className="app-card p-6">
        <h3 className="text-sm font-semibold text-app-ink">Preparation plan</h3>
        {report.preparation_plan ? (
          <p className="mt-2 text-sm text-app-ink">
            {report.preparation_plan.progress_percent}% complete (
            {report.preparation_plan.tasks_completed}/
            {report.preparation_plan.tasks_total} tasks)
          </p>
        ) : (
          <p className="mt-2 text-sm text-app-muted">
            No 7-day plan linked to this resume yet.
          </p>
        )}
      </section>

      <section className="app-card p-6">
        <h3 className="text-sm font-semibold text-app-ink">Recommended next actions</h3>
        <ul className="mt-3 list-disc pl-5 text-sm text-app-ink">
          {report.recommended_next_actions.map((action) => (
            <li key={action}>{action}</li>
          ))}
        </ul>
      </section>

      <section className="app-card p-6">
        <h3 className="text-sm font-semibold text-app-ink">Data coverage</h3>
        <ul className="mt-3 space-y-2 text-sm">
          {report.data_coverage.items.map((item) => (
            <li key={item.source} className="flex justify-between gap-2">
              <span className="text-app-ink capitalize">{item.source.replace("_", " ")}</span>
              <span className={item.available ? "text-emerald-700" : "text-app-muted"}>
                {item.available ? "Available" : "Missing"} — {item.detail}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
