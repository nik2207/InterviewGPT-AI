import Link from "next/link";

import type { JobMatchResult, SkillAlignmentItem } from "@/types/jobMatch";

function statusLabel(status: SkillAlignmentItem["match_status"]): string {
  if (status === "matched") {
    return "Matched";
  }
  if (status === "partial") {
    return "Partial";
  }
  return "Not evidenced";
}

function statusClass(status: SkillAlignmentItem["match_status"]): string {
  if (status === "matched") {
    return "bg-emerald-100 text-emerald-800";
  }
  if (status === "partial") {
    return "bg-amber-100 text-amber-900";
  }
  return "bg-slate-100 text-slate-700";
}

interface JobMatchResultsProps {
  result: JobMatchResult;
}

export function JobMatchResults({ result }: JobMatchResultsProps) {
  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-app-ink">{result.job_title}</h2>
          <p className="mt-1 text-sm text-app-muted">{result.job_description_excerpt}</p>
        </div>
        <p className="rounded-full bg-app-primary-soft px-4 py-2 text-lg font-semibold text-app-primary">
          {result.score.match_score}% match
        </p>
      </header>

      <p className="text-sm text-app-ink">{result.score.score_explanation}</p>
      <p className="text-xs text-app-muted">{result.score.scoring_rules}</p>

      <section>
        <h3 className="text-sm font-semibold text-app-ink">Skill alignment</h3>
        <ul className="mt-3 space-y-2">
          {result.skill_alignments.map((item) => (
            <li
              key={`${item.skill}-${item.requirement_type}`}
              className="rounded-control border border-app-border p-3 text-sm"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-app-ink">{item.skill}</span>
                <span className="text-xs uppercase text-app-muted">
                  {item.requirement_type}
                </span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusClass(item.match_status)}`}
                >
                  {statusLabel(item.match_status)}
                </span>
              </div>
              {item.resume_evidence ? (
                <p className="mt-2 text-app-muted">Evidence: {item.resume_evidence}</p>
              ) : null}
              {item.gap_explanation ? (
                <p className="mt-1 text-app-muted">{item.gap_explanation}</p>
              ) : null}
            </li>
          ))}
        </ul>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="rounded-control border border-app-border p-4">
          <p className="text-xs font-semibold uppercase text-app-muted">Gap summary</p>
          <p className="mt-2 text-sm text-app-ink">{result.gap_summary}</p>
        </div>
        <div className="rounded-control border border-app-border p-4">
          <p className="text-xs font-semibold uppercase text-app-muted">
            Strengths for this role
          </p>
          <ul className="mt-2 list-disc pl-5 text-sm text-app-ink">
            {result.strengths_for_role.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </section>

      <section>
        <h3 className="text-sm font-semibold text-app-ink">Job-specific interview questions</h3>
        <ol className="mt-3 list-decimal space-y-3 pl-5 text-sm text-app-ink">
          {result.interview_questions.map((item) => (
            <li key={item.question}>
              <p className="font-medium">{item.question}</p>
              <p className="text-xs text-app-muted capitalize">
                {item.category} · {item.difficulty} · evaluates {item.evaluates}
              </p>
            </li>
          ))}
        </ol>
        <Link href="/dashboard/interviews" className="btn-primary mt-4 inline-block">
          Start mock interview
        </Link>
      </section>
    </div>
  );
}
