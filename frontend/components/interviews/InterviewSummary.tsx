import type { InterviewSession } from "@/types/interview";

interface InterviewSummaryProps {
  session: InterviewSession;
}

export function InterviewSummary({ session }: InterviewSummaryProps) {
  const summary = session.summary;
  if (!summary) {
    return null;
  }

  return (
    <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-6 shadow-card">
      <h2 className="text-lg font-semibold text-emerald-900">Interview complete</h2>
      <p className="mt-2 text-sm text-emerald-800">
        Average score:{" "}
        <strong>{summary.average_score ?? "—"}</strong> / 100 across{" "}
        {summary.answered_questions} questions.
      </p>
      {summary.highlights.length > 0 ? (
        <div className="mt-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-900">
            Highlights
          </p>
          <ul className="mt-1 list-disc pl-5 text-sm text-emerald-900">
            {summary.highlights.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {summary.focus_areas.length > 0 ? (
        <div className="mt-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-900">
            Focus next
          </p>
          <ul className="mt-1 list-disc pl-5 text-sm text-emerald-900">
            {summary.focus_areas.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <p className="mt-4 text-xs text-emerald-800">{summary.scoring_rules}</p>
    </div>
  );
}
