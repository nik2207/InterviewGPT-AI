import { apiClient } from "@/lib/api/client";
import { clearAccessToken, setAccessToken } from "@/lib/auth-storage";
import type { GoogleAuthResponse, UserProfile } from "@/types/user";

export async function loginWithGoogleIdToken(
  googleIdToken: string
): Promise<GoogleAuthResponse> {
  const { data } = await apiClient.post<GoogleAuthResponse>("/auth/google", {
    token: googleIdToken,
  });
  setAccessToken(data.access_token);
  return data;
}

export async function fetchCurrentUser(): Promise<UserProfile> {
  const { data } = await apiClient.get<UserProfile>("/auth/me");
  return data;
}

export async function logoutSession(): Promise<void> {
  try {
    await apiClient.post("/auth/logout");
  } finally {
    clearAccessToken();
  }
}
