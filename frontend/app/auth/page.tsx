"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import GoogleLoginButton from "@/components/auth/GoogleLoginButton";
import { useAuth } from "@/providers/auth-provider";

export default function AuthPage() {
  const router = useRouter();
  const { status, error } = useAuth();

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/dashboard");
    }
  }, [status, router]);

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-card">
        <div className="text-center">
          <p className="text-sm font-semibold uppercase tracking-wide text-brand-600">
            InterviewGPT AI
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-slate-900">
            Sign in to continue
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Use your Google account to access your interview preparation
            dashboard.
          </p>
        </div>

        {error ? (
          <p
            className="mt-6 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900"
            role="alert"
          >
            {error}
          </p>
        ) : null}

        <div className="mt-8 flex justify-center">
          {status === "loading" ? (
            <p className="text-sm text-slate-500" aria-live="polite">
              Checking session…
            </p>
          ) : (
            <GoogleLoginButton />
          )}
        </div>
      </div>
    </main>
  );
}
