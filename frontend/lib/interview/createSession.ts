import type { CreateInterviewPayload } from "@/types/interview";

/** Backend requires 3–15 questions (schema + analysis pool). */
export function normalizeQuestionCount(value: number): number {
  if (!Number.isFinite(value)) {
    return 5;
  }
  return Math.min(15, Math.max(3, Math.round(value)));
}

export function buildCreateInterviewPayload(
  input: CreateInterviewPayload
): CreateInterviewPayload {
  return {
    ...input,
    question_count: normalizeQuestionCount(input.question_count ?? 5),
  };
}
