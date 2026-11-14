"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { fetchPlanCatalog } from "@/lib/api/billing";
import type { PlanCatalogItem } from "@/lib/api/billing";

const FEATURE_LABELS: Record<string, string> = {
  job_matching: "Job description matching",
  detailed_answer_coaching: "Detailed answer coaching",
  preparation_plans: "Personalized preparation plans",
  career_readiness: "Career readiness reports",
  voice_interview: "Voice interview mode",
  premium_analytics: "Expanded career analytics",
};

export default function PricingPage() {
  const [plans, setPlans] = useState<PlanCatalogItem[]>([]);

  useEffect(() => {
    fetchPlanCatalog()
      .then((data) => setPlans(data.plans))
      .catch(() => undefined);
  }, []);

  return (
    <div className="mx-auto max-w-5xl px-4 py-12">
      <h1 className="text-3xl font-semibold text-slate-900">Plans</h1>
      <p className="mt-2 max-w-2xl text-sm text-slate-600">
        Limits and features are enforced on the server. Payments are verified before any upgrade
        unlocks — never from the browser alone.
      </p>
      <div className="mt-8 grid gap-6 md:grid-cols-3">
        {plans.map((plan) => (
          <article
            key={plan.plan_id}
            className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
          >
            <h2 className="text-xl font-semibold text-slate-900">{plan.display_name}</h2>
            <p className="mt-2 text-2xl font-bold text-app-primary">
              {plan.price_inr === 0 ? "Free" : `₹${plan.price_inr}/mo`}
            </p>
            <ul className="mt-4 space-y-2 text-sm text-slate-700">
              <li>{plan.limits.resume_analysis} resume analyses / month</li>
              <li>{plan.limits.mock_interview} mock interviews / month</li>
              {Object.entries(plan.features)
                .filter(([, enabled]) => enabled)
                .map(([key]) => (
                  <li key={key}>{FEATURE_LABELS[key] ?? key}</li>
                ))}
            </ul>
            {plan.plan_id === "free" ? (
              <Link href="/auth" className="mt-6 inline-block text-sm text-app-primary hover:underline">
                Get started
              </Link>
            ) : (
              <Link
                href={`/dashboard/billing?upgrade=${plan.plan_id}`}
                className="mt-6 inline-block rounded-lg bg-app-primary px-4 py-2 text-sm font-medium text-white"
              >
                Upgrade
              </Link>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
