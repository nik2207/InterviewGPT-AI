"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { PreparationPlanView } from "@/components/career/PreparationPlanView";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { PageHeader } from "@/components/ui/PageHeader";
import {
  fetchPreparationPlan,
  fetchPreparationPlans,
} from "@/lib/api/preparationPlan";
import type { PreparationPlan } from "@/types/preparationPlan";

function PlanPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const planId = searchParams.get("planId");

  const [plan, setPlan] = useState<PreparationPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        if (planId) {
          setPlan(await fetchPreparationPlan(planId));
          return;
        }
        const plans = await fetchPreparationPlans();
        const active = plans.find((p) => p.status === "active") ?? plans[0];
        if (!active) {
          setPlan(null);
          return;
        }
        router.replace(`/dashboard/career/plan?planId=${active.id}`);
        setPlan(await fetchPreparationPlan(active.id));
      } catch {
        setError("Unable to load preparation plan.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [planId, router]);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        title="7-day plan"
        description="Personalised schedule with persisted task completion."
      />
      <Link href="/dashboard/career" className="text-sm text-app-primary hover:underline">
        ← Career workspace
      </Link>
      {error ? (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}
      {loading ? (
        <LoadingSkeleton rows={5} className="h-48" />
      ) : plan ? (
        <PreparationPlanView initialPlan={plan} onPlanChange={setPlan} />
      ) : (
        <p className="text-sm text-app-muted">
          No plan yet. Generate one from the{" "}
          <Link href="/dashboard/career" className="text-app-primary underline">
            career workspace
          </Link>
          .
        </p>
      )}
    </div>
  );
}

export default function PreparationPlanPage() {
  return (
    <Suspense fallback={<LoadingSkeleton rows={4} className="mx-auto max-w-6xl h-40" />}>
      <PlanPageContent />
    </Suspense>
  );
}
