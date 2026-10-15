"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  fetchCurrentUser,
  loginWithGoogleIdToken,
  logoutSession,
} from "@/lib/api/auth";
import { getAccessToken } from "@/lib/auth-storage";
import type { UserProfile } from "@/types/user";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  user: UserProfile | null;
  status: AuthStatus;
  error: string | null;
  loginWithGoogle: (googleIdToken: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [error, setError] = useState<string | null>(null);

  const refreshUser = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setUser(null);
      setStatus("unauthenticated");
      return;
    }

    try {
      const profile = await fetchCurrentUser();
      setUser(profile);
      setStatus("authenticated");
      setError(null);
    } catch {
      setUser(null);
      setStatus("unauthenticated");
      setError("Your session has expired. Please sign in again.");
    }
  }, []);

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  const loginWithGoogle = useCallback(async (googleIdToken: string) => {
    setError(null);
    setStatus("loading");
    try {
      const response = await loginWithGoogleIdToken(googleIdToken);
      setUser(response.user);
      setStatus("authenticated");
    } catch {
      setUser(null);
      setStatus("unauthenticated");
      setError("Sign-in failed. Please try again.");
      throw new Error("Sign-in failed");
    }
  }, []);

  const logout = useCallback(async () => {
    setError(null);
    try {
      await logoutSession();
    } finally {
      setUser(null);
      setStatus("unauthenticated");
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      status,
      error,
      loginWithGoogle,
      logout,
      refreshUser,
    }),
    [user, status, error, loginWithGoogle, logout, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
