export type ResumeBuilderTemplate = "classic" | "professional" | "compact";

export interface PersonalInfoSection {
  full_name: string;
  email: string;
  phone: string;
  location: string;
  linkedin: string;
  github: string;
  portfolio: string;
}

export interface EducationEntry {
  id: string;
  institution: string;
  degree: string;
  field_of_study: string;
  start_date: string;
  end_date: string;
  details: string[];
}

export interface ExperienceEntry {
  id: string;
  company: string;
  title: string;
  location: string;
  start_date: string;
  end_date: string;
  bullets: string[];
}

export interface ProjectEntry {
  id: string;
  name: string;
  url: string;
  technologies: string[];
  description: string;
  bullets: string[];
}

export interface CertificationEntry {
  id: string;
  name: string;
  issuer: string;
  date: string;
}

export interface LanguageEntry {
  id: string;
  language: string;
  proficiency: string;
}

export interface ResumeBuilderContent {
  personal_info: PersonalInfoSection;
  professional_summary: string;
  education: EducationEntry[];
  work_experience: ExperienceEntry[];
  internships: ExperienceEntry[];
  technical_skills: string[];
  projects: ProjectEntry[];
  certifications: CertificationEntry[];
  achievements: string[];
  languages: LanguageEntry[];
}

export interface ResumeBuilderVersion {
  version_number: number;
  label: string;
  content: ResumeBuilderContent;
  created_at: string;
}

export interface ResumeBuilderDetail {
  id: string;
  user_id: string;
  title: string;
  template: ResumeBuilderTemplate;
  section_order: string[];
  content: ResumeBuilderContent;
  versions: ResumeBuilderVersion[];
  source_upload_resume_id: string | null;
  disclaimer: string;
  created_at: string;
  updated_at: string;
}

export interface ResumeBuilderListItem {
  id: string;
  title: string;
  template: ResumeBuilderTemplate;
  updated_at: string;
  version_count: number;
  source_upload_resume_id: string | null;
}

export interface ResumeAiProposal {
  feature: string;
  original_text: string;
  improved_text: string;
  comparison_notes: string;
  missing_information: string[];
  keyword_suggestions: string[];
  ats_formatting_notes: string[];
  requires_user_confirmation: boolean;
  disclaimer: string;
}

export const SECTION_LABELS: Record<string, string> = {
  professional_summary: "Professional summary",
  education: "Education",
  work_experience: "Work experience",
  internships: "Internships",
  technical_skills: "Technical skills",
  projects: "Projects",
  certifications: "Certifications",
  achievements: "Achievements",
  languages: "Languages",
};

export function emptyResumeContent(): ResumeBuilderContent {
  return {
    personal_info: {
      full_name: "",
      email: "",
      phone: "",
      location: "",
      linkedin: "",
      github: "",
      portfolio: "",
    },
    professional_summary: "",
    education: [],
    work_experience: [],
    internships: [],
    technical_skills: [],
    projects: [],
    certifications: [],
    achievements: [],
    languages: [],
  };
}
