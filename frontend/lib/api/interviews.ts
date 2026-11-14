import { apiClient } from "@/lib/api/client";
import type {
  CreateInterviewPayload,
  InputMode,
  InterviewHistoryItem,
  InterviewSession,
} from "@/types/interview";
import type { InterviewTranscriptReview } from "@/types/transcript";

export async function createInterviewSession(
  payload: CreateInterviewPayload
): Promise<InterviewSession> {
  const { data } = await apiClient.post<InterviewSession>("/interviews", payload);
  return data;
}

export async function fetchAllInterviewSessions(): Promise<InterviewSession[]> {
  const { data } = await apiClient.get<{ sessions: InterviewSession[] }>(
    "/interviews"
  );
  return data.sessions;
}

export async function fetchInterviewSession(
  sessionId: string
): Promise<InterviewSession> {
  const { data } = await apiClient.get<InterviewSession>(
    `/interviews/${sessionId}`
  );
  return data;
}

export async function fetchInterviewHistory(): Promise<InterviewHistoryItem[]> {
  const { data } = await apiClient.get<{ interviews: InterviewHistoryItem[] }>(
    "/interviews/history"
  );
  return data.interviews;
}

export async function downloadInterviewReport(sessionId: string): Promise<Blob> {
  const { data } = await apiClient.get<Blob>(`/interviews/${sessionId}/report`, {
    responseType: "blob",
  });
  return data;
}

export async function submitInterviewAnswer(
  sessionId: string,
  payload: {
    submission_id: string;
    answer_text: string;
    retry_evaluation?: boolean;
    speech_metrics?: {
      input_mode: InputMode;
      duration_seconds: number | null;
    };
  }
): Promise<InterviewSession> {
  const { data } = await apiClient.post<InterviewSession>(
    `/interviews/${sessionId}/answers`,
    payload
  );
  return data;
}

export async function completeInterviewSession(
  sessionId: string
): Promise<InterviewSession> {
  const { data } = await apiClient.post<InterviewSession>(
    `/interviews/${sessionId}/complete`
  );
  return data;
}

export async function skipFollowUpQuestion(
  sessionId: string,
  questionId: string
): Promise<InterviewSession> {
  const { data } = await apiClient.post<InterviewSession>(
    `/interviews/${sessionId}/questions/${questionId}/skip`
  );
  return data;
}

export async function fetchInterviewTranscriptReview(
  sessionId: string
): Promise<InterviewTranscriptReview> {
  const { data } = await apiClient.get<InterviewTranscriptReview>(
    `/interviews/${sessionId}/transcript/review`
  );
  return data;
}

export async function updateTranscriptBookmarks(
  sessionId: string,
  questionIds: string[]
): Promise<InterviewTranscriptReview> {
  const { data } = await apiClient.patch<InterviewTranscriptReview>(
    `/interviews/${sessionId}/transcript/bookmarks`,
    { question_ids: questionIds }
  );
  return data;
}

export async function saveTranscriptPracticeRevision(
  sessionId: string,
  questionId: string,
  draftText: string
): Promise<InterviewTranscriptReview> {
  const { data } = await apiClient.put<InterviewTranscriptReview>(
    `/interviews/${sessionId}/transcript/practice/${questionId}`,
    { draft_text: draftText }
  );
  return data;
}

export async function downloadInterviewTranscript(
  sessionId: string
): Promise<Blob> {
  const { data } = await apiClient.get<Blob>(
    `/interviews/${sessionId}/transcript/export`,
    { responseType: "blob" }
  );
  return data;
}

export async function deleteInterviewSession(sessionId: string): Promise<void> {
  await apiClient.delete(`/interviews/${sessionId}`);
}
