import { apiClient } from "@/lib/api/client";

export type InstitutionRole =
  | "institution_admin"
  | "placement_officer"
  | "trainer"
  | "student";

export interface InstitutionProfile {
  id: string;
  name: string;
  slug: string;
  institution_type: string;
  website: string;
  department: string;
  course_metadata: Record<string, unknown>;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface InstitutionMembership {
  id: string;
  institution_id: string;
  user_id: string;
  role: InstitutionRole;
  department: string;
  course: string;
  batch_label: string;
  consent_share_progress: boolean;
  status: string;
  created_at: string;
}

export async function fetchMyInstitutionMemberships() {
  const { data } = await apiClient.get<
    Array<{ institution: InstitutionProfile; membership: InstitutionMembership }>
  >("/institutions/me/memberships");
  return data;
}

export async function createInstitution(payload: {
  name: string;
  institution_type?: string;
  department?: string;
}) {
  const { data } = await apiClient.post<InstitutionProfile>("/institutions", payload);
  return data;
}

export async function fetchInstitution(institutionId: string) {
  const { data } = await apiClient.get<InstitutionProfile>(
    `/institutions/${institutionId}`
  );
  return data;
}

export async function fetchInstitutionMembers(institutionId: string) {
  const { data } = await apiClient.get<{ items: InstitutionMembership[] }>(
    `/institutions/${institutionId}/members`
  );
  return data.items;
}

export async function inviteInstitutionMember(
  institutionId: string,
  payload: { email: string; role: InstitutionRole }
) {
  const { data } = await apiClient.post(`/institutions/${institutionId}/invitations`, payload);
  return data as { invite_token?: string; email: string };
}

export async function acceptInstitutionInvitation(token: string) {
  const { data } = await apiClient.post<InstitutionMembership>(
    "/institutions/invitations/accept",
    { token }
  );
  return data;
}

export async function fetchCohorts(institutionId: string) {
  const { data } = await apiClient.get<{ items: Array<Record<string, unknown>> }>(
    `/institutions/${institutionId}/cohorts`
  );
  return data.items;
}

export async function createCohort(
  institutionId: string,
  payload: { name: string; department?: string; course?: string }
) {
  const { data } = await apiClient.post(`/institutions/${institutionId}/cohorts`, payload);
  return data;
}

export async function fetchAssignments(institutionId: string) {
  const { data } = await apiClient.get<{ items: Array<Record<string, unknown>> }>(
    `/institutions/${institutionId}/assignments`
  );
  return data.items;
}

export async function createAssignment(
  institutionId: string,
  payload: { title: string; activity_type: string; cohort_id?: string; job_role?: string }
) {
  const { data } = await apiClient.post(
    `/institutions/${institutionId}/assignments`,
    payload
  );
  return data;
}

export async function fetchInstitutionAnalytics(institutionId: string) {
  const { data } = await apiClient.get(`/institutions/${institutionId}/analytics/overview`);
  return data;
}

export async function fetchStudentProgress(institutionId: string) {
  const { data } = await apiClient.get<
    Array<{
      user_id: string;
      display_name: string;
      interviews_completed: number;
      assignments_completed: number;
      consent_share_progress: boolean;
    }>
  >(`/institutions/${institutionId}/progress/students`);
  return data;
}

export async function updateSharingConsent(
  institutionId: string,
  membershipId: string,
  consent: boolean
) {
  const { data } = await apiClient.patch<InstitutionMembership>(
    `/institutions/${institutionId}/members/${membershipId}`,
    { consent_share_progress: consent }
  );
  return data;
}
