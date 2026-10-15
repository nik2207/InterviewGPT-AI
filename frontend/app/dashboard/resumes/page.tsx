"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ResumeAnalysisResults } from "@/components/resumes/ResumeAnalysisResults";
import { ResumeList } from "@/components/resumes/ResumeList";
import { ResumeUploadPanel } from "@/components/resumes/ResumeUploadPanel";
import {
  analyzeResume,
  fetchResumeAnalysis,
  fetchResumes,
} from "@/lib/api/resumes";
import { useAuth } from "@/providers/auth-provider";
import type { ResumeAnalysisResult } from "@/types/analysis";
import type { ResumeMetadata } from "@/types/resume";

function getErrorMessage(error: unknown): string {
  if (
    typeof error === "object" &&
    error !== null &&
    "response" in error
  ) {
    const axiosError = error as {
      response?: { status?: number; data?: { detail?: string } };
    };
    if (axiosError.response?.status === 401) {
      return "Your session expired. Please sign in again.";
    }
    if (axiosError.response?.status === 503) {
      return (
        axiosError.response.data?.detail ||
        "AI analysis is not configured on the server."
      );
    }
    if (axiosError.response?.status === 429) {
      return "AI quota or rate limit reached. Try again later.";
    }
    return (
      axiosError.response?.data?.detail ||
      "Unable to complete resume analysis."
    );
  }
  return "Unable to complete resume analysis.";
}

export default function ResumesPage() {
  const router = useRouter();
  const { status } = useAuth();
  const [resumes, setResumes] = useState<ResumeMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedResumeId, setSelectedResumeId] = useState<string | null>(null);
  const [analyzingResumeId, setAnalyzingResumeId] = useState<string | null>(
    null
  );
  const [analysisResult, setAnalysisResult] =
    useState<ResumeAnalysisResult | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);

  const loadResumes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchResumes();
      setResumes(response.resumes);
    } catch {
      setError("Unable to load your uploaded resumes.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/auth");
      return;
    }
    if (status === "authenticated") {
      void loadResumes();
    }
  }, [status, router, loadResumes]);

  const handleUploaded = (resume: ResumeMetadata) => {
    setResumes((current) => [resume, ...current]);
  };

  const handleAnalyze = async (resumeId: string, refresh = false) => {
    setSelectedResumeId(resumeId);
    setAnalyzingResumeId(resumeId);
    setAnalysisLoading(true);
    setAnalysisError(null);

    try {
      const result = await analyzeResume(resumeId, refresh);
      setAnalysisResult(result);
    } catch (analyzeError) {
      setAnalysisResult(null);
      setAnalysisError(getErrorMessage(analyzeError));
    } finally {
      setAnalyzingResumeId(null);
      setAnalysisLoading(false);
    }
  };

  const handleViewAnalysis = async (resumeId: string) => {
    setSelectedResumeId(resumeId);
    setAnalysisLoading(true);
    setAnalysisError(null);

    try {
      const result = await fetchResumeAnalysis(resumeId);
      setAnalysisResult(result);
    } catch (viewError) {
      setAnalysisResult(null);
      if (
        typeof viewError === "object" &&
        viewError !== null &&
        "response" in viewError &&
        (viewError as { response?: { status?: number } }).response?.status ===
          404
      ) {
        setAnalysisError("No saved analysis yet. Run Analyze resume first.");
      } else {
        setAnalysisError(getErrorMessage(viewError));
      }
    } finally {
      setAnalysisLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
          Resume analysis
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-600">
          Upload a PDF resume, then run Gemini-powered analysis to get structured
          feedback and tailored interview questions based on your resume content.
        </p>
      </header>

      <ResumeUploadPanel onUploaded={handleUploaded} />

      <ResumeList
        resumes={resumes}
        loading={loading}
        error={error}
        selectedResumeId={selectedResumeId}
        analyzingResumeId={analyzingResumeId}
        onAnalyze={handleAnalyze}
        onViewAnalysis={handleViewAnalysis}
      />

      <section aria-labelledby="analysis-results-heading">
        <h2
          id="analysis-results-heading"
          className="text-lg font-semibold text-slate-900"
        >
          Analysis results
        </h2>

        {analysisLoading ? (
          <div
            className="mt-4 rounded-xl border border-slate-200 bg-white p-6 shadow-card"
            aria-busy="true"
          >
            <p className="text-sm text-slate-600">
              Running AI analysis. This may take up to a minute…
            </p>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full w-1/2 animate-pulse rounded-full bg-brand-400" />
            </div>
          </div>
        ) : null}

        {analysisError ? (
          <p
            className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
            role="alert"
          >
            {analysisError}
          </p>
        ) : null}

        {!analysisLoading && !analysisResult && !analysisError ? (
          <p className="mt-4 rounded-xl border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-600 shadow-card">
            Select a resume and click <strong>Analyze resume</strong> to generate
            AI feedback and interview questions.
          </p>
        ) : null}

        {analysisResult && !analysisLoading ? (
          <div className="mt-4">
            <ResumeAnalysisResults result={analysisResult} />
          </div>
        ) : null}
      </section>
    </div>
  );
}
