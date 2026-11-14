export type PrepCategory = "technical" | "hr" | "coding" | "behavioural";
export type ExperienceLevel = "junior" | "mid" | "senior";
export type ContentSourceType =
  | "ai_generated_practice"
  | "catalogue_public"
  | "user_provided";

export interface CompanyPublicSource {
  label: string;
  url: string;
}

export interface CompanyPrepMaterialItem {
  title: string;
  source_type: ContentSourceType;
  source_url: string | null;
  summary: string;
}

export interface CompanyCatalogueEntry {
  id: string;
  name: string;
  aliases: string[];
  industry: string;
  headquarters: string;
  public_profile_summary: string;
  verified_public_sources: CompanyPublicSource[];
  public_prep_topics: string[];
  prep_material: CompanyPrepMaterialItem[];
}

export interface CompanyCatalogueListResponse {
  disclaimer: string;
  companies: CompanyCatalogueEntry[];
}

export interface CompanyPrepQuestion {
  id: string;
  question: string;
  prep_category: PrepCategory;
  difficulty: string;
  relevance: string;
  evaluates: string;
  source_type: ContentSourceType;
  source_label: string;
  disclaimer: string;
}

export interface ChecklistItem {
  id: string;
  label: string;
  prep_category: PrepCategory | "general";
  completed: boolean;
  source_type: ContentSourceType;
  source_label: string;
}

export interface CompanyPrepListItem {
  id: string;
  company_id: string;
  company_name: string;
  job_role: string;
  experience_level: ExperienceLevel;
  categories: PrepCategory[];
  question_count: number;
  created_at: string;
  interview_session_id: string | null;
}

export interface CompanyPrepDetail {
  id: string;
  user_id: string;
  company: CompanyCatalogueEntry;
  job_role: string;
  experience_level: ExperienceLevel;
  categories: PrepCategory[];
  user_notes: string | null;
  questions: CompanyPrepQuestion[];
  checklist: ChecklistItem[];
  interview_session_id: string | null;
  disclaimer: string;
  created_at: string;
  updated_at: string;
}

export const PREP_CATEGORY_LABELS: Record<PrepCategory, string> = {
  technical: "Technical",
  hr: "HR",
  coding: "Coding",
  behavioural: "Behavioural",
};

export const SOURCE_TYPE_LABELS: Record<ContentSourceType, string> = {
  ai_generated_practice: "AI practice",
  catalogue_public: "Public catalogue",
  user_provided: "Your notes",
};
