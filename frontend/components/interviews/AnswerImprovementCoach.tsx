"use client";

import { useMemo, useState } from "react";

import type { AnswerImprovementCoach as CoachData } from "@/types/interview";

type CoachTab =
  | "overview"
  | "missing"
  | "improved"
  | "concepts"
  | "followup";

interface AnswerImprovementCoachProps {
  originalAnswer: string;
  coach: CoachData;
  onPractice?: () => void;
}

const TABS: { id: CoachTab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "missing", label: "Missing points" },
  { id: "improved", label: "Improved answer" },
  { id: "concepts", label: "Concepts to revise" },
  { id: "followup", label: "Follow-up question" },
];

export function AnswerImprovementCoach({
  originalAnswer,
  coach,
  onPractice,
}: AnswerImprovementCoachProps) {
  const [tab, setTab] = useState<CoachTab>("overview");
  const [showCompare, setShowCompare] = useState(false);

  const starSummary = useMemo(() => {
    if (!coach.star_assessment) {
      return null;
    }
    return coach.star_assessment;
  }, [coach.star_assessment]);

  return (
    <div className="mt-4 rounded-control border border-app-border bg-app-surface p-4">
      <h4 className="text-sm font-semibold text-app-ink">Answer improvement coach</h4>

      <div className="mt-3 flex flex-wrap gap-1 border-b border-app-border pb-2">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              tab === item.id
                ? "bg-app-primary text-white"
                : "bg-app-primary-soft text-app-primary"
            }`}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="mt-4 text-sm text-app-ink">
        {tab === "overview" ? (
          <div className="space-y-3">
            <div>
              <p className="text-xs font-semibold uppercase text-app-muted">Your answer</p>
              <p className="mt-1 whitespace-pre-wrap">{originalAnswer}</p>
            </div>
            {coach.what_went_well.length > 0 ? (
              <div>
                <p className="text-xs font-semibold uppercase text-app-muted">
                  What went well
                </p>
                <ul className="mt-1 list-disc pl-5">
                  {coach.what_went_well.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            <div>
              <p className="text-xs font-semibold uppercase text-app-muted">Relevance</p>
              <p className="mt-1">{coach.relevance_to_question}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase text-app-muted">Next action</p>
              <p className="mt-1">{coach.action_to_take}</p>
            </div>
            {starSummary ? (
              <div className="rounded-control border border-app-border p-3">
                <p className="text-xs font-semibold uppercase text-app-muted">
                  STAR structure
                </p>
                <p className="mt-1">
                  {starSummary.uses_star
                    ? "STAR elements detected in your answer."
                    : "STAR structure is missing or incomplete."}
                </p>
                {starSummary.missing_star_elements.length > 0 ? (
                  <p className="mt-1 text-app-muted">
                    Missing: {starSummary.missing_star_elements.join(", ")}
                  </p>
                ) : null}
                {starSummary.specificity_suggestions.length > 0 ? (
                  <ul className="mt-2 list-disc pl-5 text-app-muted">
                    {starSummary.specificity_suggestions.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}

        {tab === "missing" ? (
          <div className="space-y-3">
            {coach.missing_important_points.length > 0 ? (
              <ul className="list-disc pl-5">
                {coach.missing_important_points.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p className="text-app-muted">No major gaps flagged.</p>
            )}
            {coach.incorrect_or_unclear.length > 0 ? (
              <div>
                <p className="text-xs font-semibold uppercase text-app-muted">
                  Incorrect or unclear
                </p>
                <ul className="mt-1 list-disc pl-5">
                  {coach.incorrect_or_unclear.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : null}

        {tab === "improved" ? (
          <div className="space-y-3">
            <p className="text-app-muted">{coach.why_example_is_stronger}</p>
            <p className="whitespace-pre-wrap rounded-control border border-app-border bg-white p-3">
              {coach.improved_example_answer}
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-secondary text-xs"
                onClick={() => setShowCompare((v) => !v)}
              >
                {showCompare ? "Hide comparison" : "Compare with your answer"}
              </button>
              {onPractice ? (
                <button type="button" className="btn-primary text-xs" onClick={onPractice}>
                  Practise this improvement
                </button>
              ) : null}
            </div>
            {showCompare ? (
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-control border border-app-border p-3">
                  <p className="text-xs font-semibold text-app-muted">Your answer</p>
                  <p className="mt-1 whitespace-pre-wrap">{originalAnswer}</p>
                </div>
                <div className="rounded-control border border-emerald-200 bg-emerald-50/50 p-3">
                  <p className="text-xs font-semibold text-emerald-800">
                    Suggested answer
                  </p>
                  <p className="mt-1 whitespace-pre-wrap">
                    {coach.improved_example_answer}
                  </p>
                </div>
              </div>
            ) : null}
          </div>
        ) : null}

        {tab === "concepts" ? (
          coach.concepts_to_revise.length > 0 ? (
            <ul className="list-disc pl-5">
              {coach.concepts_to_revise.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : (
            <p className="text-app-muted">No extra concepts flagged for this answer.</p>
          )
        ) : null}

        {tab === "followup" ? (
          <div className="space-y-3">
            <p className="font-medium">{coach.follow_up_practice_question}</p>
            <p className="text-app-muted">{coach.action_to_take}</p>
            {onPractice ? (
              <button type="button" className="btn-primary text-xs" onClick={onPractice}>
                Practise with this follow-up
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
