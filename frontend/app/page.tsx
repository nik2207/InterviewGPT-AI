"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/providers/auth-provider";

export default function HomePage() {
  const router = useRouter();
  const { status } = useAuth();

  useEffect(() => {
    if (status === "loading") {
      return;
    }
    router.replace(status === "authenticated" ? "/dashboard" : "/auth");
  }, [status, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-sm text-slate-500" aria-live="polite">
        Loading…
      </p>
    </div>
  );
}
