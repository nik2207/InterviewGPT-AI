import { AnswerImprovementCoach } from "@/components/interviews/AnswerImprovementCoach";
import type { AnswerEvaluation } from "@/types/interview";

interface InterviewFeedbackProps {
  evaluation: AnswerEvaluation;
  originalAnswer?: string;
  onPracticeImprovement?: () => void;
}

export function InterviewFeedback({
  evaluation,
  originalAnswer = "",
  onPracticeImprovement,
}: InterviewFeedbackProps) {
  const dimensions = evaluation.dimension_scores;
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-card">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-900">Feedback</h3>
        <p className="text-sm font-medium text-brand-700">
          Score: {evaluation.overall_score}/100
        </p>
      </div>
      <p className="mt-2 text-sm text-slate-700">{evaluation.feedback_summary}</p>
      {evaluation.language_fluency_feedback ? (
        <p className="mt-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
          <span className="font-semibold text-slate-800">Language / clarity: </span>
          {evaluation.language_fluency_feedback}
        </p>
      ) : null}
      <dl className="mt-4 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <div>Technical correctness: {dimensions.technical_correctness}/5</div>
        <div>Relevance: {dimensions.relevance}/5</div>
        <div>Completeness: {dimensions.completeness}/5</div>
        <div>Structure: {dimensions.answer_structure}/5</div>
      </dl>
      {evaluation.strengths.length > 0 ? (
        <div className="mt-3">
          <p className="text-xs font-semibold text-slate-800">Strengths</p>
          <ul className="mt-1 list-disc pl-5 text-sm text-slate-700">
            {evaluation.strengths.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {evaluation.improvement_suggestions.length > 0 ? (
        <div className="mt-3">
          <p className="text-xs font-semibold text-slate-800">Improve</p>
          <ul className="mt-1 list-disc pl-5 text-sm text-slate-700">
            {evaluation.improvement_suggestions.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {evaluation.improvement_coach && originalAnswer ? (
        <AnswerImprovementCoach
          originalAnswer={originalAnswer}
          coach={evaluation.improvement_coach}
          onPractice={onPracticeImprovement}
        />
      ) : null}
    </div>
  );
}
