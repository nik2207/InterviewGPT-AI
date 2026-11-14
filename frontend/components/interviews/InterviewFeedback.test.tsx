import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { InterviewFeedback } from "@/components/interviews/InterviewFeedback";
import type { AnswerEvaluation } from "@/types/interview";

const baseEvaluation: AnswerEvaluation = {
  dimension_scores: {
    technical_correctness: 4,
    relevance: 4,
    completeness: 3,
    answer_structure: 4,
  },
  strengths: ["Clear structure"],
  missing_concepts: ["Metrics"],
  improvement_suggestions: ["Add numbers"],
  feedback_summary: "Solid answer.",
  overall_score: 82,
  scoring_rules: "rules",
  improvement_coach: {
    what_went_well: ["Clear structure"],
    missing_important_points: ["Impact metrics"],
    incorrect_or_unclear: [],
    relevance_to_question: "On topic.",
    improved_example_answer: "A stronger version with metrics.",
    why_example_is_stronger: "Shows outcomes.",
    concepts_to_revise: ["SLOs"],
    follow_up_practice_question: "How do you measure success?",
    action_to_take: "Add one metric.",
  },
};

describe("InterviewFeedback", () => {
  it("renders improvement coach tabs when coach data is present", () => {
    render(
      <InterviewFeedback
        evaluation={baseEvaluation}
        originalAnswer="My original answer"
      />
    );
    expect(screen.getByText("Answer improvement coach")).toBeInTheDocument();
    expect(screen.getByText("Overview")).toBeInTheDocument();
    expect(screen.getByText("My original answer")).toBeInTheDocument();
  });
});
