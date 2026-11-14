import { LANGUAGE_LABELS } from "@/lib/speech/locales";
import type { InterviewLanguageSettings } from "@/types/interview";

interface InterviewLanguageIndicatorsProps {
  settings: InterviewLanguageSettings;
  compact?: boolean;
}

export function InterviewLanguageIndicators({
  settings,
  compact = false,
}: InterviewLanguageIndicatorsProps) {
  const items = [
    { label: "Questions", code: settings.question_language },
    { label: "Answers", code: settings.answer_language },
    { label: "Feedback", code: settings.feedback_language },
  ];

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
      {items.map((item) => (
        <span
          key={item.label}
          className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1"
        >
          {!compact ? `${item.label}: ` : null}
          {LANGUAGE_LABELS[item.code]}
        </span>
      ))}
      {settings.allow_bilingual_answers ? (
        <span className="rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-indigo-800">
          Bilingual OK
        </span>
      ) : null}
      {settings.practice_professional_english ? (
        <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-emerald-900">
          English phrasing practice
        </span>
      ) : null}
    </div>
  );
}
