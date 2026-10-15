"use client";

import { useRef, useState } from "react";

import { MAX_RESUME_FILE_BYTES, uploadResume } from "@/lib/api/resumes";
import type { ResumeMetadata } from "@/types/resume";

interface ResumeUploadPanelProps {
  onUploaded: (resume: ResumeMetadata) => void;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(2)} MiB`;
}

export function ResumeUploadPanel({ onUploaded }: ResumeUploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const validateFile = (file: File): string | null => {
    const isPdf =
      file.type === "application/pdf" ||
      file.name.toLowerCase().endsWith(".pdf");
    if (!isPdf) {
      return "Only PDF files are supported.";
    }
    if (file.size === 0) {
      return "The selected file is empty.";
    }
    if (file.size > MAX_RESUME_FILE_BYTES) {
      return "File exceeds the 5 MiB maximum upload size.";
    }
    return null;
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setSuccess(null);
    setError(null);
    setProgress(0);
    if (!file) {
      setSelectedFile(null);
      return;
    }
    const validationError = validateFile(file);
    if (validationError) {
      setSelectedFile(null);
      setError(validationError);
      return;
    }
    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError("Choose a PDF resume to upload.");
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(null);
    setProgress(0);

    try {
      const response = await uploadResume(selectedFile, setProgress);
      setSuccess(response.message);
      onUploaded(response.resume);
      setSelectedFile(null);
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    } catch (uploadError: unknown) {
      if (
        typeof uploadError === "object" &&
        uploadError !== null &&
        "response" in uploadError
      ) {
        const axiosError = uploadError as {
          response?: { status?: number; data?: { detail?: string } };
        };
        if (axiosError.response?.status === 401) {
          setError("Your session expired. Please sign in again.");
        } else {
          setError(
            axiosError.response?.data?.detail ||
              "Upload failed. Please try again."
          );
        }
      } else {
        setError("Upload failed. Please try again.");
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <section
      className="rounded-xl border border-slate-200 bg-white p-6 shadow-card"
      aria-labelledby="resume-upload-heading"
    >
      <h2
        id="resume-upload-heading"
        className="text-lg font-semibold text-slate-900"
      >
        Upload resume (PDF)
      </h2>
      <p className="mt-2 text-sm text-slate-600">
        PDF only. Maximum size: 5 MiB. Text is extracted for future AI analysis.
        OCR for scanned resumes is not supported yet.
      </p>

      <div className="mt-5 space-y-4">
        <input
          ref={inputRef}
          id="resume-file"
          type="file"
          accept="application/pdf,.pdf"
          onChange={handleFileChange}
          disabled={uploading}
          className="block w-full text-sm text-slate-700 file:mr-4 file:rounded-lg file:border-0 file:bg-brand-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-brand-700 hover:file:bg-brand-100"
          aria-describedby="resume-upload-help"
        />
        <p id="resume-upload-help" className="text-xs text-slate-500">
          {selectedFile
            ? `Selected: ${selectedFile.name} (${formatBytes(selectedFile.size)})`
            : "No file selected"}
        </p>

        {uploading ? (
          <div aria-live="polite">
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>Uploading…</span>
              <span>{progress}%</span>
            </div>
            <div
              className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={progress}
              aria-label="Upload progress"
            >
              <div
                className="h-full rounded-full bg-brand-500 transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        ) : null}

        {error ? (
          <p
            className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
            role="alert"
          >
            {error}
          </p>
        ) : null}

        {success ? (
          <p
            className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800"
            role="status"
          >
            {success}
          </p>
        ) : null}

        <button
          type="button"
          onClick={handleUpload}
          disabled={!selectedFile || uploading}
          className="inline-flex items-center justify-center rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
        >
          {uploading ? "Uploading…" : "Upload resume"}
        </button>

        <p className="text-xs text-slate-500">
          Uploads are stored securely for your account. Use Analyze resume
          below to generate AI feedback.
        </p>
      </div>
    </section>
  );
}
