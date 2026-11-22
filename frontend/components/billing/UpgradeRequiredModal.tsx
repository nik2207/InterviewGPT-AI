"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export function UpgradeRequiredModal() {
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const handleUpgradeRequired = (event: Event) => {
      const detail = (event as CustomEvent<string>).detail;
      setMessage(detail || "This action needs an active plan or more AI credits.");
    };
    window.addEventListener("app:upgrade-required", handleUpgradeRequired);
    return () => window.removeEventListener("app:upgrade-required", handleUpgradeRequired);
  }, []);

  if (!message) return null;

  return (
    <div className="fixed inset-0 z-[120] flex items-center justify-center bg-slate-950/60 p-4">
      <section
        aria-labelledby="upgrade-required-title"
        aria-modal="true"
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl sm:p-8"
        role="dialog"
      >
        <p className="text-sm font-semibold text-app-primary">Plan or credit limit reached</p>
        <h2 id="upgrade-required-title" className="mt-2 text-2xl font-bold text-app-ink">
          Continue your preparation
        </h2>
        <p className="mt-3 text-sm leading-6 text-app-muted" role="alert">{message}</p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/dashboard/billing" className="btn-primary" onClick={() => setMessage(null)}>
            View plans and credits
          </Link>
          <button type="button" className="btn-secondary" onClick={() => setMessage(null)}>
            Close
          </button>
        </div>
      </section>
    </div>
  );
}
