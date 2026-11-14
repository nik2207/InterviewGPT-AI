export type ApplicationStatus =
  | "interested"
  | "applied"
  | "assessment"
  | "interview_scheduled"
  | "interview_completed"
  | "offer_received"
  | "rejected"
  | "withdrawn";

export type EmploymentType =
  | "full_time"
  | "part_time"
  | "contract"
  | "internship"
  | "freelance"
  | "other";

export const APPLICATION_STATUS_LABELS: Record<ApplicationStatus, string> = {
  interested: "Interested",
  applied: "Applied",
  assessment: "Assessment",
  interview_scheduled: "Interview Scheduled",
  interview_completed: "Interview Completed",
  offer_received: "Offer Received",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

export const APPLICATION_STATUS_ORDER: ApplicationStatus[] = [
  "interested",
  "applied",
  "assessment",
  "interview_scheduled",
  "interview_completed",
  "offer_received",
  "rejected",
  "withdrawn",
];

export const EMPLOYMENT_TYPE_LABELS: Record<EmploymentType, string> = {
  full_time: "Full time",
  part_time: "Part time",
  contract: "Contract",
  internship: "Internship",
  freelance: "Freelance",
  other: "Other",
};

export interface InterviewDateEntry {
  id: string;
  label: string;
  scheduled_at: string;
  notes: string;
}

export interface JobApplication {
  id: string;
  user_id: string;
  company: string;
  job_title: string;
  job_description: string;
  job_posting_url: string | null;
  location: string;
  employment_type: EmploymentType;
  application_date: string | null;
  status: ApplicationStatus;
  resume_id: string | null;
  job_match_id: string | null;
  interview_dates: InterviewDateEntry[];
  notes: string;
  follow_up_date: string | null;
  interview_session_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobApplicationListResponse {
  items: JobApplication[];
  total: number;
  page: number;
  page_size: number;
  disclaimer: string;
}

export interface JobApplicationStats {
  total: number;
  by_status: Record<string, number>;
  upcoming_interviews: {
    application_id: string;
    company: string;
    job_title: string;
    label?: string;
    scheduled_at: string;
  }[];
  upcoming_follow_ups: {
    application_id: string;
    company: string;
    job_title: string;
    follow_up_date: string;
  }[];
  disclaimer: string;
}

export interface CreateJobApplicationPayload {
  company: string;
  job_title: string;
  job_description?: string;
  job_posting_url?: string | null;
  location?: string;
  employment_type?: EmploymentType;
  application_date?: string | null;
  status?: ApplicationStatus;
  resume_id?: string | null;
  job_match_id?: string | null;
  interview_dates?: InterviewDateEntry[];
  notes?: string;
  follow_up_date?: string | null;
}

export type UpdateJobApplicationPayload = Partial<CreateJobApplicationPayload>;
