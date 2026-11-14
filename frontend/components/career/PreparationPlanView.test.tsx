import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PreparationPlanView } from "@/components/career/PreparationPlanView";
import type { PreparationPlan } from "@/types/preparationPlan";

vi.mock("@/lib/api/preparationPlan", () => ({
  updatePlanTaskCompletion: vi.fn(),
  regeneratePreparationPlan: vi.fn(),
}));

const samplePlan: PreparationPlan = {
  id: "p1",
  user_id: "u1",
  resume_id: "r1",
  job_match_id: null,
  status: "active",
  daily_study_minutes: 45,
  model: "test",
  plan_start_date: "2026-01-01",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  plan_summary: "Focus on Python gaps.",
  priority_gaps: ["K8s"],
  progress_percent: 0,
  tasks_completed: 0,
  tasks_total: 2,
  today_day_number: 1,
  days: [
    {
      day_number: 1,
      relative_label: "Day 1",
      scheduled_date: "2026-01-01",
      theme: "Identify and prioritise gaps",
      learning_objective: "Map gaps",
      skills_to_practice: ["Python"],
      learning_activities: ["List gaps"],
      interview_questions: ["Why this role?"],
      practical_exercise: null,
      estimated_duration_minutes: 45,
      completion_criteria: "Gap list written",
      day_completed: false,
      tasks: [
        {
          task_id: "d1-learn-1",
          title: "Learning activity 1",
          description: "List gaps",
          task_type: "learning",
          estimated_minutes: 20,
          completed: false,
          completed_at: null,
        },
      ],
    },
  ],
};

describe("PreparationPlanView", () => {
  it("shows progress and today recommendation", () => {
    render(
      <PreparationPlanView initialPlan={samplePlan} onPlanChange={() => undefined} />
    );
    expect(screen.getByText("7-day preparation plan")).toBeInTheDocument();
    expect(screen.getByText(/Today's focus/i)).toBeInTheDocument();
  });
});
