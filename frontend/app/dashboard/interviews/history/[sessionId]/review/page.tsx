"use client";

import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { InterviewTranscriptReviewView } from "@/components/interviews/InterviewTranscriptReviewView";
import {
  deleteInterviewSession,
  fetchInterviewTranscriptReview,
} from "@/lib/api/interviews";
import type { InterviewTranscriptReview } from "@/types/transcript";

function getErrorMessage(error: unknown): string {
  if (
    typeof error === "object" &&
    error !== null &&
    "response" in error &&
    typeof (error as { response?: { data?: { detail?: string } } }).response
      ?.data?.detail === "string"
  ) {
    return (error as { response: { data: { detail: string } } }).response.data.detail;
  }
  return "Something went wrong. Please try again.";
}

export default function InterviewTranscriptReviewPage() {
  const params = useParams<{ sessionId: string }>();
  const sessionId = params.sessionId;
  const router = useRouter();

  const [review, setReview] = useState<InterviewTranscriptReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchInterviewTranscriptReview(sessionId);
      setReview(data);
    } catch (loadError) {
      setError(getErrorMessage(loadError));
      setReview(null);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleDeleteConfirmed() {
    setDeleting(true);
    setError(null);
    try {
      await deleteInterviewSession(sessionId);
      router.push("/dashboard/interviews/history");
    } catch (deleteError) {
      setError(getErrorMessage(deleteError));
      setConfirmDelete(false);
    } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-slate-500">Loading transcript review…</p>;
  }

  if (!review) {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        <p className="text-sm text-red-600" role="alert">
          {error ?? "Transcript not found."}
        </p>
        <Link href="/dashboard/interviews/history" className="text-sm text-brand-700">
          Back to history
        </Link>
      </div>
    );
  }

  return (
    <div className="pb-10">
      <InterviewTranscriptReviewView
        sessionId={sessionId}
        review={review}
        onReviewChange={setReview}
        onDeleted={() => setConfirmDelete(true)}
      />
      {confirmDelete ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="max-w-md rounded-xl bg-white p-5 shadow-lg">
            <h2 className="text-lg font-semibold text-slate-900">Delete interview?</h2>
            <p className="mt-2 text-sm text-slate-600">{review.audio_retention_policy}</p>
            <div className="mt-4 flex gap-2">
              <button
                type="button"
                className="btn-secondary"
                disabled={deleting}
                onClick={() => setConfirmDelete(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-60"
                disabled={deleting}
                onClick={handleDeleteConfirmed}
              >
                {deleting ? "Deleting…" : "Delete permanently"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
