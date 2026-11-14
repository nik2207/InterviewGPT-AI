import type { InterviewAnswer, InterviewQuestion } from "@/types/interview";
import { InterviewFeedback } from "@/components/interviews/InterviewFeedback";

interface InterviewCoachingPanelProps {
  question: InterviewQuestion | null;
  lastFeedback: InterviewAnswer | null;
  submitting: boolean;
  onPracticeImprovement?: () => void;
}

export function InterviewCoachingPanel({
  question,
  lastFeedback,
  submitting,
  onPracticeImprovement,
}: InterviewCoachingPanelProps) {
  const evaluation = lastFeedback?.evaluation;
  const matchesCurrent =
    evaluation &&
    question &&
    lastFeedback?.question_id === question.id;

  return (
    <aside className="app-card flex h-full flex-col p-4 lg:sticky lg:top-4 lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto">
      <h2 className="text-sm font-semibold text-app-ink">Coaching panel</h2>

      <section className="mt-4">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-app-muted">
          Question context
        </h3>
        {question ? (
          <div className="mt-2 text-sm text-app-ink">
            <p className="font-medium">{question.category}</p>
            <p className="mt-1 text-app-muted">{question.evaluates}</p>
            <p className="mt-2 text-xs text-app-muted">
              Relevance: {question.relevance}
            </p>
          </div>
        ) : (
          <p className="mt-2 text-sm text-app-muted">No active question.</p>
        )}
      </section>

      <section className="mt-5">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-app-muted">
          Answer feedback
        </h3>
        {submitting ? (
          <p className="mt-2 text-sm text-app-muted" aria-live="polite">
            Evaluating your answer…
          </p>
        ) : null}
        {matchesCurrent && evaluation ? (
          <div className="mt-2">
            <InterviewFeedback
              evaluation={evaluation}
              originalAnswer={lastFeedback.answer_text}
              onPracticeImprovement={onPracticeImprovement}
            />
          </div>
        ) : lastFeedback?.evaluation_status === "failed" &&
          lastFeedback.question_id === question?.id ? (
          <p className="mt-2 text-sm text-amber-800">
            Evaluation failed. Your answer was saved — use retry evaluation.
          </p>
        ) : (
          <p className="mt-2 text-sm text-app-muted">
            Submit an answer to see strengths, scores and improvement tips.
          </p>
        )}
      </section>

      <section className="mt-5 border-t border-app-border pt-4">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-app-muted">
          Hints
        </h3>
        <p className="mt-2 text-sm text-app-muted">
          Structured hints per question are not available yet. Use the question
          context and evaluation feedback after you submit.
        </p>
      </section>
    </aside>
  );
}
