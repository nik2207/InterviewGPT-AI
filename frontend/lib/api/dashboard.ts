import {
  fetchAllInterviewSessions,
  fetchInterviewHistory,
  fetchInterviewSession,
} from "@/lib/api/interviews";
import type { DashboardStats, InterviewActivityItem } from "@/types/dashboard";

export interface SkillGapInsight {
  label: string;
  evidence: string;
  source: "evaluation" | "resume";
}

export interface ScoreTrendPoint {
  label: string;
  score: number;
}

/**
 * Practice sessions = all interview sessions (in progress + completed).
 */
export async function fetchDashboardStats(): Promise<DashboardStats> {
  const [history, sessions] = await Promise.all([
    fetchInterviewHistory(),
    fetchAllInterviewSessions(),
  ]);

  const scored = history.filter((item) => item.overall_score !== null);
  const averageScore =
    scored.length > 0
      ? Math.round(
          (scored.reduce((sum, item) => sum + (item.overall_score ?? 0), 0) /
            scored.length) *
            10
        ) / 10
      : null;

  return {
    interviewsCompleted: history.length,
    practiceSessions: sessions.length,
    averageScore,
    preparationProgressPercent: null,
  };
}

export async function fetchRecentInterviewActivity(): Promise<
  InterviewActivityItem[]
> {
  const history = await fetchInterviewHistory();
  return history.slice(0, 6).map((item) => ({
    id: item.id,
    title: item.role,
    completedAt: new Date(item.completed_at).toLocaleString(),
    score: item.overall_score,
    questionCount: item.question_count,
  }));
}

export async function fetchScoreTrend(): Promise<ScoreTrendPoint[]> {
  const history = await fetchInterviewHistory();
  return history
    .filter((h) => h.overall_score !== null)
    .slice(0, 8)
    .reverse()
    .map((item) => ({
      label: new Date(item.completed_at).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      }),
      score: item.overall_score ?? 0,
    }));
}

export async function fetchSkillGapInsights(): Promise<SkillGapInsight[]> {
  const history = await fetchInterviewHistory();
  if (history.length === 0) {
    return [];
  }
  try {
    const session = await fetchInterviewSession(history[0].id);
    const gaps: SkillGapInsight[] = [];
    for (const answer of session.answers) {
      if (!answer.evaluation) {
        continue;
      }
      for (const concept of answer.evaluation.missing_concepts.slice(0, 2)) {
        gaps.push({
          label: concept,
          evidence: "Identified in a recent mock interview answer evaluation.",
          source: "evaluation",
        });
      }
      for (const suggestion of answer.evaluation.improvement_suggestions.slice(
        0,
        1
      )) {
        gaps.push({
          label: "Improvement area",
          evidence: suggestion,
          source: "evaluation",
        });
      }
    }
    const unique = new Map<string, SkillGapInsight>();
    for (const item of gaps) {
      unique.set(item.evidence, item);
    }
    return Array.from(unique.values()).slice(0, 6);
  } catch {
    return [];
  }
}
