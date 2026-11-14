import { apiClient } from "@/lib/api/client";
import type {
  InterviewerTone,
  VoiceClarificationResult,
  VoiceInterviewState,
  VoiceSessionStatus,
  VoiceTranscriptRole,
} from "@/types/interview";

export async function appendVoiceTranscript(
  sessionId: string,
  payload: {
    role: VoiceTranscriptRole;
    text: string;
    question_id?: string;
  }
): Promise<VoiceInterviewState> {
  const { data } = await apiClient.post<VoiceInterviewState>(
    `/interviews/${sessionId}/voice/transcript`,
    payload
  );
  return data;
}

export async function updateVoiceSessionStatus(
  sessionId: string,
  session_status: VoiceSessionStatus
): Promise<VoiceInterviewState> {
  const { data } = await apiClient.patch<VoiceInterviewState>(
    `/interviews/${sessionId}/voice/status`,
    { session_status }
  );
  return data;
}

export async function requestVoiceClarification(
  sessionId: string,
  payload: { question_id: string; answer_draft: string }
): Promise<VoiceClarificationResult> {
  const { data } = await apiClient.post<VoiceClarificationResult>(
    `/interviews/${sessionId}/voice/clarification`,
    payload
  );
  return data;
}

export type { InterviewerTone };
