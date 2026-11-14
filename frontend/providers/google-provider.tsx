"use client";

import { GoogleOAuthProvider } from "@react-oauth/google";

const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

export default function GoogleProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  if (!clientId) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6 text-center text-sm text-red-600">
        Missing NEXT_PUBLIC_GOOGLE_CLIENT_ID. Add it to frontend/.env.local.
      </div>
    );
  }

  return (
    <GoogleOAuthProvider clientId={clientId}>{children}</GoogleOAuthProvider>
  );
}
