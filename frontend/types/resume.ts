export type ParsingStatus = "parsed" | "failed";

export interface ResumeMetadata {
  id: string;
  original_filename: string;
  file_size_bytes: number;
  uploaded_at: string;
  page_count: number;
  parsing_status: ParsingStatus;
}

export interface ResumeUploadResponse {
  resume: ResumeMetadata;
  message: string;
}

export interface ResumeListResponse {
  resumes: ResumeMetadata[];
}
