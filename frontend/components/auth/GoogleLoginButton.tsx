"use client";

import { GoogleLogin } from "@react-oauth/google";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/providers/auth-provider";

export default function GoogleLoginButton() {
  const router = useRouter();
  const { loginWithGoogle } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSuccess = async (credentialResponse: { credential?: string }) => {
    if (!credentialResponse.credential) {
      setLocalError("Google did not return a sign-in credential.");
      return;
    }

    setIsSubmitting(true);
    setLocalError(null);

    try {
      await loginWithGoogle(credentialResponse.credential);
      router.push("/dashboard");
    } catch {
      setLocalError("Unable to sign in. Check your connection and try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex w-full max-w-sm flex-col items-center gap-4">
      {localError ? (
        <p
          className="w-full rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
          role="alert"
        >
          {localError}
        </p>
      ) : null}
      <div
        className={isSubmitting ? "pointer-events-none opacity-60" : undefined}
        aria-busy={isSubmitting}
      >
        <GoogleLogin
          onSuccess={handleSuccess}
          onError={() => setLocalError("Google sign-in was cancelled or failed.")}
          useOneTap={false}
          theme="outline"
          size="large"
          text="continue_with"
          shape="rectangular"
        />
      </div>
    </div>
  );
}
