"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState, type ReactNode } from "react";

import { ResumeBuilderPreview } from "@/components/resumes/ResumeBuilderPreview";
import { getApiErrorMessage } from "@/lib/api/errors";
import {
  aiAtsFormatting,
  aiImproveBullets,
  aiImproveProject,
  aiImproveSummary,
  aiJobKeywords,
  aiMissingInfo,
  downloadResumeBuilderPdf,
  fetchResumeBuilder,
  saveResumeBuilderVersion,
  updateResumeBuilder,
} from "@/lib/api/resumeBuilder";
import type {
  ResumeAiProposal,
  ResumeBuilderContent,
  ResumeBuilderDetail,
  ResumeBuilderTemplate,
} from "@/types/resumeBuilder";
import { SECTION_LABELS } from "@/types/resumeBuilder";

function newId(): string {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID().replace(/-/g, "").slice(0, 12)
    : `id${Date.now()}`;
}

export default function ResumeBuilderEditorPage() {
  const params = useParams<{ id: string }>();
  const docId = params.id;

  const [doc, setDoc] = useState<ResumeBuilderDetail | null>(null);
  const [content, setContent] = useState<ResumeBuilderContent | null>(null);
  const [activeSection, setActiveSection] = useState("personal_info");
  const [saving, setSaving] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [proposal, setProposal] = useState<ResumeAiProposal | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [pendingBulletExpId, setPendingBulletExpId] = useState<string | null>(null);
  const [pendingProjectId, setPendingProjectId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchResumeBuilder(docId);
      setDoc(data);
      setContent(data.content);
    } catch (cause: unknown) {
      setError(getApiErrorMessage(cause));
    }
  }, [docId]);

  useEffect(() => {
    load();
  }, [load]);

  async function saveDraft(): Promise<boolean> {
    if (!doc || !content) return false;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await updateResumeBuilder(doc.id, {
        title: doc.title,
        template: doc.template,
        section_order: doc.section_order,
        content,
      });
      setDoc(updated);
      setContent(updated.content);
      setNotice("Draft saved.");
      return true;
    } catch (cause: unknown) {
      setError(getApiErrorMessage(cause));
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function saveVersion() {
    if (!(await saveDraft()) || !doc) return;
    try {
      const updated = await saveResumeBuilderVersion(doc.id, `Version ${doc.versions.length + 1}`);
      setDoc(updated);
      setNotice(`Version ${updated.versions.length} saved.`);
    } catch (cause: unknown) {
      setError(getApiErrorMessage(cause));
    }
  }

  async function downloadPdf() {
    if (!doc) return;
    try {
      const blob = await downloadResumeBuilderPdf(doc.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `resume-${doc.id.slice(0, 10)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      setNotice("PDF downloaded.");
    } catch (cause: unknown) {
      setError(getApiErrorMessage(cause));
    }
  }

  function moveSection(key: string, direction: -1 | 1) {
    if (!doc) return;
    const order = [...doc.section_order];
    const index = order.indexOf(key);
    if (index < 0) return;
    const target = index + direction;
    if (target < 0 || target >= order.length) return;
    [order[index], order[target]] = [order[target], order[index]];
    setDoc({ ...doc, section_order: order });
  }

  function applyProposal() {
    if (!proposal || !content) return;
    if (proposal.feature === "improve_summary") {
      setContent({ ...content, professional_summary: proposal.improved_text });
    } else if (proposal.feature === "improve_bullets" && pendingBulletExpId) {
      const bullets = proposal.improved_text.split("\n").map((b) => b.replace(/^•\s*/, "").trim()).filter(Boolean);
      const updateList = (list: typeof content.work_experience) =>
        list.map((e) => (e.id === pendingBulletExpId ? { ...e, bullets } : e));
      setContent({
        ...content,
        work_experience: updateList(content.work_experience),
        internships: updateList(content.internships),
      });
    } else if (proposal.feature === "improve_project" && pendingProjectId) {
      setContent({
        ...content,
        projects: content.projects.map((p) =>
          p.id === pendingProjectId
            ? { ...p, description: proposal.improved_text }
            : p
        ),
      });
    }
    setPendingBulletExpId(null);
    setPendingProjectId(null);
    setProposal(null);
  }

  if (!doc || !content) {
    return <p className="text-sm text-slate-500">{error ?? "Loading editor…"}</p>;
  }

  return (
    <div className="mx-auto max-w-7xl space-y-4 pb-12">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link href="/dashboard/resumes/builder" className="text-sm text-brand-700">
            ← Builder list
          </Link>
          <input
            aria-label="Resume title"
            className="mt-2 block w-full max-w-md rounded-xl border border-slate-200 bg-white px-3 py-2 text-xl font-semibold text-slate-900 shadow-sm"
            value={doc.title}
            onChange={(e) => setDoc({ ...doc, title: e.target.value })}
          />
          <p className="text-xs text-slate-500">{doc.disclaimer}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <select
            className="rounded-control border border-slate-200 px-2 py-1 text-sm"
            value={doc.template}
            onChange={(e) =>
              setDoc({ ...doc, template: e.target.value as ResumeBuilderTemplate })
            }
          >
            <option value="classic">Classic template</option>
            <option value="professional">Professional template</option>
            <option value="compact">Compact template</option>
          </select>
          <button type="button" className="btn-secondary" disabled={saving} onClick={() => void saveDraft()}>
            {saving ? "Saving…" : "Save draft"}
          </button>
          <button type="button" className="btn-secondary" onClick={saveVersion}>
            Save version
          </button>
          <button type="button" className="btn-primary" onClick={downloadPdf}>
            Download PDF
          </button>
        </div>
      </div>

      {error ? (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
          {error}
        </p>
      ) : null}
      {notice ? (
        <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800" role="status">
          {notice}
        </p>
      ) : null}

      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(400px,0.9fr)]">
        <div className="app-card space-y-4 p-4 sm:p-5">
          <nav className="flex flex-wrap gap-2 border-b border-app-border pb-3 text-xs" aria-label="Resume sections">
            <button
              type="button"
              aria-pressed={activeSection === "personal_info"}
              className={`rounded-full px-3 py-2 font-medium transition ${activeSection === "personal_info" ? "bg-app-primary text-white" : "text-app-muted hover:bg-app-primary-soft hover:text-app-primary"}`}
              onClick={() => setActiveSection("personal_info")}
            >
              Personal
            </button>
            {doc.section_order.map((key) => (
              <button
                key={key}
                type="button"
                aria-pressed={activeSection === key}
                className={`rounded-full px-3 py-2 font-medium transition ${activeSection === key ? "bg-app-primary text-white" : "text-app-muted hover:bg-app-primary-soft hover:text-app-primary"}`}
                onClick={() => setActiveSection(key)}
              >
                {SECTION_LABELS[key]}
              </button>
            ))}
          </nav>

          {activeSection === "personal_info" ? (
            <div className="grid gap-2 text-sm">
              {(
                [
                  ["full_name", "Full name"],
                  ["email", "Email"],
                  ["phone", "Phone"],
                  ["location", "Location"],
                  ["linkedin", "LinkedIn"],
                  ["github", "GitHub"],
                  ["portfolio", "Portfolio"],
                ] as const
              ).map(([field, label]) => (
                <label key={field} className="block">
                  {label}
                  <input
                    className="mt-1 w-full rounded border border-slate-200 px-2 py-1"
                    value={content.personal_info[field]}
                    onChange={(e) =>
                      setContent({
                        ...content,
                        personal_info: {
                          ...content.personal_info,
                          [field]: e.target.value,
                        },
                      })
                    }
                  />
                </label>
              ))}
            </div>
          ) : null}

          {activeSection === "professional_summary" ? (
            <div className="space-y-2">
              <textarea
                className="w-full rounded border border-slate-200 p-2 text-sm"
                rows={6}
                value={content.professional_summary}
                onChange={(e) =>
                  setContent({ ...content, professional_summary: e.target.value })
                }
              />
              <button
                type="button"
                className="btn-secondary text-sm"
                disabled={aiBusy}
                onClick={async () => {
                  setAiBusy(true);
                  try {
                    setProposal(await aiImproveSummary(doc.id));
                  } finally {
                    setAiBusy(false);
                  }
                }}
              >
                AI improve summary
              </button>
            </div>
          ) : null}

          {activeSection === "technical_skills" ? (
            <textarea
              className="w-full rounded border border-slate-200 p-2 text-sm"
              rows={4}
              value={content.technical_skills.join(", ")}
              onChange={(e) =>
                setContent({
                  ...content,
                  technical_skills: e.target.value
                    .split(",")
                    .map((s) => s.trim())
                    .filter(Boolean),
                })
              }
              placeholder="Comma-separated skills"
            />
          ) : null}

          {(activeSection === "work_experience" || activeSection === "internships") && (
            <ExperienceEditor
              entries={
                activeSection === "work_experience"
                  ? content.work_experience
                  : content.internships
              }
              onChange={(entries) =>
                setContent({
                  ...content,
                  [activeSection]: entries,
                })
              }
              onImproveBullets={async (experienceId) => {
                setPendingBulletExpId(experienceId);
                setAiBusy(true);
                try {
                  setProposal(
                    await aiImproveBullets(
                      doc.id,
                      experienceId,
                      activeSection === "work_experience"
                        ? "work_experience"
                        : "internships"
                    )
                  );
                } finally {
                  setAiBusy(false);
                }
              }}
            />
          )}

          {activeSection === "education" && (
            <ListSectionEditor
              label="Education"
              addLabel="Add education"
              onAdd={() =>
                setContent({
                  ...content,
                  education: [
                    ...content.education,
                    {
                      id: newId(),
                      institution: "",
                      degree: "",
                      field_of_study: "",
                      start_date: "",
                      end_date: "",
                      details: [],
                    },
                  ],
                })
              }
            >
              {content.education.map((edu, index) => (
                <div key={edu.id} className="rounded border border-slate-100 p-2 text-sm">
                  <input
                    className="mb-1 w-full rounded border px-2 py-1"
                    placeholder="Institution"
                    value={edu.institution}
                    onChange={(e) => {
                      const copy = [...content.education];
                      copy[index] = { ...edu, institution: e.target.value };
                      setContent({ ...content, education: copy });
                    }}
                  />
                  <input
                    className="mb-1 w-full rounded border px-2 py-1"
                    placeholder="Degree"
                    value={edu.degree}
                    onChange={(e) => {
                      const copy = [...content.education];
                      copy[index] = { ...edu, degree: e.target.value };
                      setContent({ ...content, education: copy });
                    }}
                  />
                </div>
              ))}
            </ListSectionEditor>
          )}

          {activeSection === "certifications" && (
            <ListSectionEditor
              label="Certifications"
              addLabel="Add certification"
              onAdd={() =>
                setContent({
                  ...content,
                  certifications: [
                    ...content.certifications,
                    { id: newId(), name: "", issuer: "", date: "" },
                  ],
                })
              }
            >
              {content.certifications.map((cert, index) => (
                <input
                  key={cert.id}
                  className="mb-1 w-full rounded border px-2 py-1 text-sm"
                  placeholder="Name — Issuer (date)"
                  value={`${cert.name} — ${cert.issuer} (${cert.date})`}
                  onChange={(e) => {
                    const copy = [...content.certifications];
                    copy[index] = { ...cert, name: e.target.value };
                    setContent({ ...content, certifications: copy });
                  }}
                />
              ))}
            </ListSectionEditor>
          )}

          {activeSection === "achievements" && (
            <textarea
              className="w-full rounded border border-slate-200 p-2 text-sm"
              rows={5}
              value={content.achievements.join("\n")}
              onChange={(e) =>
                setContent({
                  ...content,
                  achievements: e.target.value.split("\n").filter(Boolean),
                })
              }
              placeholder="One achievement per line"
            />
          )}

          {activeSection === "languages" && (
            <ListSectionEditor
              label="Languages"
              addLabel="Add language"
              onAdd={() =>
                setContent({
                  ...content,
                  languages: [
                    ...content.languages,
                    { id: newId(), language: "", proficiency: "" },
                  ],
                })
              }
            >
              {content.languages.map((lang, index) => (
                <div key={lang.id} className="flex gap-2 text-sm">
                  <input
                    className="w-full rounded border px-2 py-1"
                    placeholder="Language"
                    value={lang.language}
                    onChange={(e) => {
                      const copy = [...content.languages];
                      copy[index] = { ...lang, language: e.target.value };
                      setContent({ ...content, languages: copy });
                    }}
                  />
                  <input
                    className="w-full rounded border px-2 py-1"
                    placeholder="Proficiency"
                    value={lang.proficiency}
                    onChange={(e) => {
                      const copy = [...content.languages];
                      copy[index] = { ...lang, proficiency: e.target.value };
                      setContent({ ...content, languages: copy });
                    }}
                  />
                </div>
              ))}
            </ListSectionEditor>
          )}

          {activeSection === "projects" && (
            <ProjectsEditor
              projects={content.projects}
              onChange={(projects) => setContent({ ...content, projects })}
              onImprove={async (projectId) => {
                setPendingProjectId(projectId);
                setAiBusy(true);
                try {
                  setProposal(await aiImproveProject(doc.id, projectId));
                } finally {
                  setAiBusy(false);
                }
              }}
            />
          )}

          <div className="border-t border-slate-100 pt-3 text-sm">
            <p className="font-medium text-slate-800">AI assistant</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-secondary text-xs"
                disabled={aiBusy}
                onClick={async () => setProposal(await aiMissingInfo(doc.id))}
              >
                Missing info
              </button>
              <button
                type="button"
                className="btn-secondary text-xs"
                disabled={aiBusy}
                onClick={async () => setProposal(await aiAtsFormatting(doc.id))}
              >
                ATS formatting tips
              </button>
            </div>
            <textarea
              className="mt-2 w-full rounded border border-slate-200 p-2 text-xs"
              rows={3}
              placeholder="Paste job description for keyword suggestions…"
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
            />
            <button
              type="button"
              className="btn-secondary mt-1 text-xs"
              disabled={aiBusy || jobDescription.length < 80}
              onClick={async () =>
                setProposal(await aiJobKeywords(doc.id, jobDescription))
              }
            >
              Suggest keywords
            </button>
          </div>

          <div className="text-xs text-slate-500">
            <p className="font-medium">Section order</p>
            <ul className="mt-1 space-y-1">
              {doc.section_order.map((key) => (
                <li key={key} className="flex items-center gap-2">
                  <span>{SECTION_LABELS[key]}</span>
                  <button type="button" onClick={() => moveSection(key, -1)}>
                    ↑
                  </button>
                  <button type="button" onClick={() => moveSection(key, 1)}>
                    ↓
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <ResumeBuilderPreview
          title={doc.title}
          template={doc.template}
          content={content}
          sectionOrder={doc.section_order}
        />
      </div>

      {doc.versions.length > 0 ? (
        <div className="app-card p-4 text-sm">
          <h3 className="font-semibold">Version history</h3>
          <ul className="mt-2 space-y-1 text-slate-600">
            {doc.versions.map((v) => (
              <li key={v.version_number}>
                v{v.version_number}: {v.label} — {new Date(v.created_at).toLocaleString()}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {proposal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="max-h-[90vh] max-w-lg overflow-y-auto rounded-xl bg-white p-5 shadow-lg">
            <h2 className="text-lg font-semibold">Review AI suggestion</h2>
            <p className="mt-1 text-xs text-slate-500">{proposal.disclaimer}</p>
            <p className="mt-3 text-sm font-medium">Comparison</p>
            <p className="text-sm text-slate-600">{proposal.comparison_notes}</p>
            {proposal.improved_text ? (
              <textarea
                className="mt-2 w-full rounded border border-slate-200 p-2 text-sm"
                rows={5}
                value={proposal.improved_text}
                onChange={(e) =>
                  setProposal({ ...proposal, improved_text: e.target.value })
                }
              />
            ) : null}
            {proposal.missing_information.length > 0 ? (
              <ul className="mt-2 list-disc pl-5 text-sm">
                {proposal.missing_information.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : null}
            {proposal.keyword_suggestions.length > 0 ? (
              <p className="mt-2 text-sm">
                Keywords: {proposal.keyword_suggestions.join(", ")}
              </p>
            ) : null}
            {proposal.ats_formatting_notes.length > 0 ? (
              <ul className="mt-2 list-disc pl-5 text-sm">
                {proposal.ats_formatting_notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            ) : null}
            <div className="mt-4 flex gap-2">
              <button type="button" className="btn-secondary" onClick={() => setProposal(null)}>
                Discard
              </button>
              <button type="button" className="btn-primary" onClick={applyProposal}>
                Apply to draft (confirm)
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function ListSectionEditor({
  label,
  addLabel,
  onAdd,
  children,
}: {
  label: string;
  addLabel: string;
  onAdd: () => void;
  children: ReactNode;
}) {
  return (
    <div className="space-y-2 text-sm">
      <p className="font-medium text-slate-800">{label}</p>
      {children}
      <button type="button" className="btn-secondary text-xs" onClick={onAdd}>
        {addLabel}
      </button>
    </div>
  );
}

function ExperienceEditor({
  entries,
  onChange,
  onImproveBullets,
}: {
  entries: ResumeBuilderContent["work_experience"];
  onChange: (e: ResumeBuilderContent["work_experience"]) => void;
  onImproveBullets: (id: string) => void;
}) {
  return (
    <div className="space-y-3 text-sm">
      {entries.map((entry, index) => (
        <div key={entry.id} className="rounded border border-slate-100 p-2">
          <input
            className="mb-1 w-full rounded border px-2 py-1"
            placeholder="Title"
            value={entry.title}
            onChange={(e) => {
              const copy = [...entries];
              copy[index] = { ...entry, title: e.target.value };
              onChange(copy);
            }}
          />
          <input
            className="mb-1 w-full rounded border px-2 py-1"
            placeholder="Company"
            value={entry.company}
            onChange={(e) => {
              const copy = [...entries];
              copy[index] = { ...entry, company: e.target.value };
              onChange(copy);
            }}
          />
          <textarea
            className="w-full rounded border px-2 py-1"
            rows={3}
            placeholder="Bullets (one per line)"
            value={entry.bullets.join("\n")}
            onChange={(e) => {
              const copy = [...entries];
              copy[index] = {
                ...entry,
                bullets: e.target.value.split("\n").filter(Boolean),
              };
              onChange(copy);
            }}
          />
          <button
            type="button"
            className="mt-1 text-xs text-brand-700"
            onClick={() => onImproveBullets(entry.id)}
          >
            AI improve bullets
          </button>
        </div>
      ))}
      <button
        type="button"
        className="btn-secondary text-xs"
        onClick={() =>
          onChange([
            ...entries,
            {
              id: newId(),
              company: "",
              title: "",
              location: "",
              start_date: "",
              end_date: "",
              bullets: [],
            },
          ])
        }
      >
        Add entry
      </button>
    </div>
  );
}

function ProjectsEditor({
  projects,
  onChange,
  onImprove,
}: {
  projects: ResumeBuilderContent["projects"];
  onChange: (p: ResumeBuilderContent["projects"]) => void;
  onImprove: (id: string) => void;
}) {
  return (
    <div className="space-y-3 text-sm">
      {projects.map((project, index) => (
        <div key={project.id} className="rounded border border-slate-100 p-2">
          <input
            className="mb-1 w-full rounded border px-2 py-1"
            placeholder="Project name"
            value={project.name}
            onChange={(e) => {
              const copy = [...projects];
              copy[index] = { ...project, name: e.target.value };
              onChange(copy);
            }}
          />
          <textarea
            className="w-full rounded border px-2 py-1"
            rows={3}
            value={project.description}
            onChange={(e) => {
              const copy = [...projects];
              copy[index] = { ...project, description: e.target.value };
              onChange(copy);
            }}
          />
          <button type="button" className="text-xs text-brand-700" onClick={() => onImprove(project.id)}>
            AI improve project
          </button>
        </div>
      ))}
      <button
        type="button"
        className="btn-secondary text-xs"
        onClick={() =>
          onChange([
            ...projects,
            {
              id: newId(),
              name: "",
              url: "",
              technologies: [],
              description: "",
              bullets: [],
            },
          ])
        }
      >
        Add project
      </button>
    </div>
  );
}
