"use client";

import { useCallback, useMemo, useState } from "react";

import {
  regeneratePreparationPlan,
  updatePlanTaskCompletion,
} from "@/lib/api/preparationPlan";
import type { PreparationPlan, PreparationPlanDay } from "@/types/preparationPlan";

interface PreparationPlanViewProps {
  initialPlan: PreparationPlan;
  onPlanChange: (plan: PreparationPlan) => void;
}

export function PreparationPlanView({
  initialPlan,
  onPlanChange,
}: PreparationPlanViewProps) {
  const [plan, setPlan] = useState(initialPlan);
  const [selectedDay, setSelectedDay] = useState(
    initialPlan.today_day_number ?? 1
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const todayDay = useMemo(
    () => plan.days.find((d) => d.day_number === selectedDay),
    [plan.days, selectedDay]
  );

  const syncPlan = useCallback(
    (next: PreparationPlan) => {
      setPlan(next);
      onPlanChange(next);
    },
    [onPlanChange]
  );

  async function toggleTask(day: PreparationPlanDay, taskId: string, completed: boolean) {
    setBusy(true);
    setError(null);
    try {
      const updated = await updatePlanTaskCompletion(
        plan.id,
        day.day_number,
        taskId,
        completed
      );
      syncPlan(updated);
    } catch {
      setError("Could not save task completion. Try again.");
    } finally {
      setBusy(false);
    }
  }

  async function handleRegenerate() {
    if (
      !window.confirm(
        "Regenerate creates a new plan and archives this one. Completed tasks will not carry over."
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const next = await regeneratePreparationPlan(plan.id);
      syncPlan(next);
      setSelectedDay(next.today_day_number ?? 1);
    } catch {
      setError("Regeneration failed.");
    } finally {
      setBusy(false);
    }
  }

  const recommendedDay = plan.today_day_number;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-app-ink">7-day preparation plan</h2>
          <p className="mt-1 text-sm text-app-muted">{plan.plan_summary}</p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-semibold text-app-primary">
            {plan.progress_percent}%
          </p>
          <p className="text-xs text-app-muted">
            {plan.tasks_completed}/{plan.tasks_total} tasks done
          </p>
        </div>
      </header>

      <div
        className="h-2 w-full overflow-hidden rounded-full bg-app-border"
        role="progressbar"
        aria-valuenow={plan.progress_percent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full bg-app-primary transition-all"
          style={{ width: `${plan.progress_percent}%` }}
        />
      </div>

      {recommendedDay ? (
        <div className="rounded-control border border-app-primary/30 bg-app-primary-soft/30 px-4 py-3 text-sm text-app-ink">
          <span className="font-medium">Today&apos;s focus:</span> Day {recommendedDay} —{" "}
          {plan.days.find((d) => d.day_number === recommendedDay)?.theme}
          <button
            type="button"
            className="ml-3 text-app-primary underline"
            onClick={() => setSelectedDay(recommendedDay)}
          >
            Open day
          </button>
        </div>
      ) : null}

      {plan.priority_gaps.length > 0 ? (
        <p className="text-sm text-app-muted">
          Priority gaps: {plan.priority_gaps.join(", ")}
        </p>
      ) : null}

      {error ? (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}

      <ol className="flex gap-2 overflow-x-auto pb-2">
        {plan.days.map((day) => (
          <li key={day.day_number}>
            <button
              type="button"
              disabled={busy}
              onClick={() => setSelectedDay(day.day_number)}
              className={`min-w-[5.5rem] rounded-control border px-3 py-2 text-left text-xs ${
                selectedDay === day.day_number
                  ? "border-app-primary bg-app-primary text-white"
                  : "border-app-border bg-white text-app-ink"
              }`}
            >
              <span className="block font-semibold">Day {day.day_number}</span>
              <span className="block opacity-80">
                {day.day_completed ? "Done" : "Pending"}
              </span>
            </button>
          </li>
        ))}
      </ol>

      {todayDay ? (
        <section className="app-card p-6">
          <p className="text-xs font-semibold uppercase text-app-muted">{todayDay.theme}</p>
          <h3 className="mt-1 text-lg font-medium text-app-ink">
            {todayDay.relative_label} · {todayDay.scheduled_date}
          </h3>
          <p className="mt-2 text-sm text-app-ink">{todayDay.learning_objective}</p>
          <p className="mt-2 text-xs text-app-muted">
            ~{todayDay.estimated_duration_minutes} min · Skills:{" "}
            {todayDay.skills_to_practice.join(", ")}
          </p>

          <ul className="mt-6 space-y-3">
            {todayDay.tasks.map((task) => (
              <li
                key={task.task_id}
                className={`rounded-control border p-4 text-sm ${
                  task.completed
                    ? "border-emerald-200 bg-emerald-50/50"
                    : "border-app-border bg-white"
                }`}
              >
                <label className="flex cursor-pointer items-start gap-3">
                  <input
                    type="checkbox"
                    className="mt-1"
                    disabled={busy || plan.status === "archived"}
                    checked={task.completed}
                    onChange={(e) =>
                      toggleTask(todayDay, task.task_id, e.target.checked)
                    }
                  />
                  <span>
                    <span className="font-medium text-app-ink">{task.title}</span>
                    <span className="ml-2 text-xs capitalize text-app-muted">
                      {task.task_type.replace("_", " ")} · {task.estimated_minutes}m
                    </span>
                    <p className="mt-1 text-app-muted">{task.description}</p>
                  </span>
                </label>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-xs text-app-muted">
            Completion criteria: {todayDay.completion_criteria}
          </p>
        </section>
      ) : null}

      {plan.status === "active" ? (
        <button
          type="button"
          className="btn-secondary"
          disabled={busy}
          onClick={handleRegenerate}
        >
          Regenerate plan
        </button>
      ) : (
        <p className="text-sm text-app-muted">This plan is archived (read-only).</p>
      )}
    </div>
  );
}
