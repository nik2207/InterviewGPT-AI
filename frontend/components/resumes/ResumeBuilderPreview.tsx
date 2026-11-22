import type { ResumeBuilderContent, ResumeBuilderTemplate } from "@/types/resumeBuilder";
import { SECTION_LABELS } from "@/types/resumeBuilder";

interface ResumeBuilderPreviewProps {
  title: string;
  template: ResumeBuilderTemplate;
  content: ResumeBuilderContent;
  sectionOrder: string[];
}

export function ResumeBuilderPreview({
  title,
  template,
  content,
  sectionOrder,
}: ResumeBuilderPreviewProps) {
  const fontClass =
    template === "professional"
      ? "font-serif"
      : template === "compact"
        ? "text-[13px]"
        : "font-sans";

  const { personal_info: p } = content;
  const hasResumeDetails = Boolean(
    content.professional_summary.trim() ||
      content.education.length ||
      content.work_experience.length ||
      content.internships.length ||
      content.technical_skills.length ||
      content.projects.length ||
      content.certifications.length ||
      content.achievements.length ||
      content.languages.length
  );

  return (
    <article
      className={`mx-auto min-h-[680px] w-full max-w-xl self-start rounded-xl border border-slate-200 bg-white p-8 shadow-lg sm:p-10 ${fontClass}`}
      aria-label="Resume preview"
    >
      <header className="border-b border-slate-200 pb-3">
        <h1 className="text-xl font-semibold text-slate-900">
          {p.full_name.trim() || title}
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          {[p.email, p.phone, p.location].filter(Boolean).join(" · ")}
        </p>
        <p className="text-xs text-slate-500">
          {[p.linkedin, p.github, p.portfolio].filter(Boolean).join(" · ")}
        </p>
      </header>

      {!hasResumeDetails ? (
        <div className="mt-6 rounded-xl border border-dashed border-violet-300 bg-violet-50/70 p-5" role="status">
          <p className="text-sm font-semibold text-slate-900">Your resume is taking shape</p>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            Add a summary, skills, education, or experience from the editor. Your sections will appear here as you fill them in.
          </p>
        </div>
      ) : null}

      {sectionOrder.map((key) => {
        if (key === "professional_summary" && content.professional_summary.trim()) {
          return (
            <section key={key} className="mt-4">
              <h2 className="text-xs font-bold uppercase tracking-wide text-slate-800">
                {SECTION_LABELS[key]}
              </h2>
              <p className="mt-1 text-sm text-slate-700">{content.professional_summary}</p>
            </section>
          );
        }
        if (key === "technical_skills" && content.technical_skills.length > 0) {
          return (
            <section key={key} className="mt-4">
              <h2 className="text-xs font-bold uppercase tracking-wide text-slate-800">
                {SECTION_LABELS[key]}
              </h2>
              <p className="mt-1 text-sm text-slate-700">
                {content.technical_skills.join(", ")}
              </p>
            </section>
          );
        }
        if (key === "work_experience" || key === "internships") {
          const entries =
            key === "work_experience" ? content.work_experience : content.internships;
          if (entries.length === 0) return null;
          return (
            <section key={key} className="mt-4">
              <h2 className="text-xs font-bold uppercase tracking-wide text-slate-800">
                {SECTION_LABELS[key]}
              </h2>
              {entries.map((e) => (
                <div key={e.id} className="mt-2">
                  <p className="text-sm font-medium text-slate-900">
                    {e.title}
                    {e.company ? ` — ${e.company}` : ""}
                  </p>
                  <p className="text-xs text-slate-500">
                    {[e.location, `${e.start_date} – ${e.end_date}`]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                  <ul className="mt-1 list-disc pl-5 text-sm text-slate-700">
                    {e.bullets.map((b) => (
                      <li key={b}>{b}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </section>
          );
        }
        if (key === "education" && content.education.length > 0) {
          return (
            <section key={key} className="mt-4">
              <h2 className="text-xs font-bold uppercase tracking-wide text-slate-800">
                {SECTION_LABELS[key]}
              </h2>
              {content.education.map((edu) => (
                <div key={edu.id} className="mt-2 text-sm text-slate-700">
                  <p className="font-medium">
                    {edu.degree} — {edu.institution}
                  </p>
                  <p className="text-xs text-slate-500">
                    {edu.start_date} – {edu.end_date}
                  </p>
                </div>
              ))}
            </section>
          );
        }
        if (key === "projects" && content.projects.length > 0) {
          return (
            <section key={key} className="mt-4">
              <h2 className="text-xs font-bold uppercase tracking-wide text-slate-800">
                {SECTION_LABELS[key]}
              </h2>
              {content.projects.map((proj) => (
                <div key={proj.id} className="mt-2 text-sm text-slate-700">
                  <p className="font-medium">{proj.name}</p>
                  <p>{proj.description}</p>
                </div>
              ))}
            </section>
          );
        }
        if (key === "certifications" && content.certifications.length > 0) {
          return (
            <section key={key} className="mt-4">
              <h2 className="text-xs font-bold uppercase tracking-wide text-slate-800">
                {SECTION_LABELS[key]}
              </h2>
              <ul className="mt-1 text-sm text-slate-700">
                {content.certifications.map((c) => (
                  <li key={c.id}>
                    {c.name} — {c.issuer} ({c.date})
                  </li>
                ))}
              </ul>
            </section>
          );
        }
        if (key === "achievements" && content.achievements.length > 0) {
          return (
            <section key={key} className="mt-4">
              <h2 className="text-xs font-bold uppercase tracking-wide text-slate-800">
                {SECTION_LABELS[key]}
              </h2>
              <ul className="mt-1 list-disc pl-5 text-sm text-slate-700">
                {content.achievements.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            </section>
          );
        }
        if (key === "languages" && content.languages.length > 0) {
          return (
            <section key={key} className="mt-4">
              <h2 className="text-xs font-bold uppercase tracking-wide text-slate-800">
                {SECTION_LABELS[key]}
              </h2>
              <ul className="mt-1 text-sm text-slate-700">
                {content.languages.map((lang) => (
                  <li key={lang.id}>
                    {lang.language} — {lang.proficiency}
                  </li>
                ))}
              </ul>
            </section>
          );
        }
        return null;
      })}
    </article>
  );
}
