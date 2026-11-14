import axios from "axios";

import { apiClient } from "@/lib/api/client";
import { getAccessToken } from "@/lib/auth-storage";
import type { ResumeAnalysisResult } from "@/types/analysis";
import type { ResumeListResponse, ResumeUploadResponse } from "@/types/resume";

const baseURL = process.env.NEXT_PUBLIC_API_URL;

export const MAX_RESUME_FILE_BYTES = 5 * 1024 * 1024;

export async function fetchResumes(): Promise<ResumeListResponse> {
  const { data } = await apiClient.get<ResumeListResponse>("/resumes");
  return data;
}

export async function uploadResume(
  file: File,
  onProgress?: (percent: number) => void
): Promise<ResumeUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const token = getAccessToken();
  const { data } = await axios.post<ResumeUploadResponse>(
    `${baseURL}/resumes/upload`,
    formData,
    {
      headers: token
        ? {
            Authorization: `Bearer ${token}`,
          }
        : undefined,
      onUploadProgress: (event) => {
        if (!event.total) {
          return;
        }
        const percent = Math.round((event.loaded / event.total) * 100);
        onProgress?.(percent);
      },
    }
  );

  return data;
}

export async function analyzeResume(
  resumeId: string,
  refresh = false
): Promise<ResumeAnalysisResult> {
  const { data } = await apiClient.post<ResumeAnalysisResult>(
    `/resumes/${resumeId}/analyze`,
    null,
    { params: { refresh } }
  );
  return data;
}

export async function fetchResumeAnalysis(
  resumeId: string
): Promise<ResumeAnalysisResult> {
  const { data } = await apiClient.get<ResumeAnalysisResult>(
    `/resumes/${resumeId}/analysis`
  );
  return data;
}
