import type { ResumeAnalysisResult } from "@/types/analysis";

interface ResumeAnalysisResultsProps {
  result: ResumeAnalysisResult;
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-card">
      <h3 className="text-base font-semibold text-slate-900">{title}</h3>
      <div className="mt-3 text-sm text-slate-700">{children}</div>
    </section>
  );
}

function BulletList({ items }: { items: string[] }) {
  if (items.length === 0) {
    return <p className="text-slate-500">None noted.</p>;
  }
  return (
    <ul className="list-disc space-y-1 pl-5">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export function ResumeAnalysisResults({ result }: ResumeAnalysisResultsProps) {
  const { analysis } = result;

  return (
    <div className="space-y-4" aria-live="polite">
      {result.cached ? (
        <p className="rounded-lg border border-brand-100 bg-brand-50 px-3 py-2 text-sm text-brand-800">
          Showing the latest saved analysis for this resume.
        </p>
      ) : null}

      <Section title="Professional summary">
        <p>{analysis.professional_summary}</p>
      </Section>

      <div className="grid gap-4 lg:grid-cols-2">
        <Section title="Skills">
          <BulletList items={analysis.skills} />
        </Section>
        <Section title="Strengths">
          <BulletList items={analysis.strengths} />
        </Section>
      </div>

      <Section title="Experience analysis">
        <p className="whitespace-pre-wrap">{analysis.experience_analysis}</p>
      </Section>

      <Section title="Projects analysis">
        <p className="whitespace-pre-wrap">{analysis.projects_analysis}</p>
      </Section>

      <div className="grid gap-4 lg:grid-cols-2">
        <Section title="Areas to improve">
          <BulletList items={analysis.areas_to_improve} />
        </Section>
        <Section title="Missing or unclear information">
          <BulletList items={analysis.missing_or_unclear_information} />
        </Section>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Section title="ATS & readability suggestions">
          <BulletList items={analysis.ats_readability_suggestions} />
        </Section>
        <Section title="Recommended roles">
          <BulletList items={analysis.role_recommendations} />
        </Section>
      </div>

      <Section title="Skill gaps">
        <BulletList items={analysis.skill_gaps} />
      </Section>

      <section
        className="rounded-xl border border-slate-200 bg-white p-5 shadow-card"
        aria-labelledby="interview-questions-heading"
      >
        <h3
          id="interview-questions-heading"
          className="text-base font-semibold text-slate-900"
        >
          Tailored interview questions
        </h3>
        <p className="mt-1 text-xs text-slate-500">
          Generated from your resume content. These are practice prompts, not
          guaranteed real interview questions.
        </p>
        <ul className="mt-4 space-y-4">
          {result.interview_questions.map((item, index) => (
            <li
              key={`${item.question}-${index}`}
              className="rounded-lg border border-slate-100 p-4"
            >
              <p className="font-medium text-slate-900">{item.question}</p>
              <p className="mt-2 text-xs text-slate-500">
                {item.category} · {item.difficulty}
              </p>
              <p className="mt-2 text-sm text-slate-600">
                <span className="font-medium">Relevance:</span> {item.relevance}
              </p>
              <p className="mt-1 text-sm text-slate-600">
                <span className="font-medium">Evaluates:</span> {item.evaluates}
              </p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
