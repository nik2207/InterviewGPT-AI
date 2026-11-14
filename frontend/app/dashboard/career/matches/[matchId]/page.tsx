"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { JobMatchResults } from "@/components/career/JobMatchResults";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { PageHeader } from "@/components/ui/PageHeader";
import { fetchJobMatch } from "@/lib/api/jobMatch";
import type { JobMatchResult } from "@/types/jobMatch";

export default function JobMatchDetailPage() {
  const params = useParams<{ matchId: string }>();
  const [result, setResult] = useState<JobMatchResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchJobMatch(params.matchId)
      .then(setResult)
      .catch(() => setError("Unable to load this job match."))
      .finally(() => setLoading(false));
  }, [params.matchId]);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        title="Job match results"
        description="Explainable alignment between your resume and a target role."
      />
      <Link href="/dashboard/career" className="text-sm text-app-primary hover:underline">
        ← Back to career workspace
      </Link>
      {error ? (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}
      {loading ? (
        <LoadingSkeleton rows={4} className="h-40" />
      ) : result ? (
        <section className="app-card p-6">
          <JobMatchResults result={result} />
        </section>
      ) : null}
    </div>
  );
}
