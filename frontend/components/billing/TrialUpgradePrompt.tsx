"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { fetchBillingOverview } from "@/lib/api/billing";
import type { UserProfile } from "@/types/user";

export function TrialUpgradePrompt({ user }: { user: UserProfile }) {
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [daysLeft, setDaysLeft] = useState<number | null>(null);

  useEffect(() => {
    const trialEnd = user.trial_ends_at
      ? new Date(user.trial_ends_at)
      : new Date(new Date(user.created_at).getTime() + 7 * 24 * 60 * 60 * 1000);
    const remaining = trialEnd.getTime() - Date.now();
    if (!Number.isFinite(remaining)) return;
    const promptKey = `trial-upgrade-prompt:${user.id}`;
    const checkExpiredTrial = () => {
      if (window.sessionStorage.getItem(promptKey)) return;
      fetchBillingOverview()
        .then((overview) => {
          if (overview.effective_plan_id === "free") setShowUpgrade(true);
        })
        .catch(() => undefined);
    };
    if (remaining > 0) {
      setDaysLeft(Math.ceil(remaining / (24 * 60 * 60 * 1000)));
      const timer = window.setTimeout(checkExpiredTrial, remaining);
      return () => window.clearTimeout(timer);
    }

    checkExpiredTrial();
  }, [user.created_at, user.id, user.trial_ends_at]);

  function dismiss() {
    window.sessionStorage.setItem(`trial-upgrade-prompt:${user.id}`, "shown");
    setShowUpgrade(false);
  }

  return (
    <>
      {daysLeft !== null ? (
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-violet-200 bg-violet-50 px-4 py-3 text-sm text-violet-950">
          <span>
            {daysLeft === 1
              ? "Your all-features trial ends in about a day."
              : `${daysLeft} days left in your all-features trial.`}
          </span>
          <Link href="/dashboard/billing" className="font-semibold underline underline-offset-2">
            View plans
          </Link>
        </div>
      ) : null}

      {showUpgrade ? (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/60 p-4" role="presentation">
          <section
            aria-labelledby="trial-ended-title"
            aria-modal="true"
            className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl sm:p-8"
            role="dialog"
          >
            <p className="text-sm font-semibold text-app-primary">Your 7-day trial has ended</p>
            <h2 id="trial-ended-title" className="mt-2 text-2xl font-bold text-app-ink">
              Keep your preparation moving
            </h2>
            <p className="mt-3 text-sm leading-6 text-app-muted">
              Choose a plan to continue using interviews, coaching, preparation plans, and the other premium tools.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link href="/dashboard/billing" className="btn-primary" onClick={dismiss}>
                Compare plans
              </Link>
              <button type="button" className="btn-secondary" onClick={dismiss}>
                Continue with free plan
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </>
  );
}
