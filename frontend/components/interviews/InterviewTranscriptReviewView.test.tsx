import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { InterviewTranscriptReviewView } from "@/components/interviews/InterviewTranscriptReviewView";
import type { InterviewTranscriptReview } from "@/types/transcript";

vi.mock("@/lib/api/interviews", () => ({
  updateTranscriptBookmarks: vi.fn(),
  saveTranscriptPracticeRevision: vi.fn(),
  downloadInterviewTranscript: vi.fn(),
  downloadInterviewReport: vi.fn(),
}));

const review: InterviewTranscriptReview = {
  session_id: "sess1",
  role: "Backend Engineer",
  status: "completed",
  completed_at: "2026-01-01T00:00:00Z",
  bookmarks: [],
  items: [
    {
      sequence: 1,
      question: {
        id: "q1",
        question: "Explain Redis caching?",
        category: "technical",
        difficulty: "intermediate",
        relevance: "Cache",
        evaluates: "Depth",
        is_follow_up: false,
      },
      answer: {
        question_id: "q1",
        submission_id: "s1",
        answer_text: "We use Redis for hot keys.",
        submitted_at: "2026-01-01T00:01:00Z",
        evaluation_status: "evaluated",
        evaluation: null,
        evaluated_at: null,
        evaluation_error: null,
      },
      answer_status: "answered",
      is_weak: true,
      is_bookmarked: false,
      timing: null,
      voice_transcript: [],
      audio_recording_available: false,
      practice_revision: null,
    },
    {
      sequence: 2,
      question: {
        id: "q2",
        question: "Describe a leadership moment?",
        category: "behavioral",
        difficulty: "intermediate",
        relevance: "STAR",
        evaluates: "Leadership",
        is_follow_up: false,
      },
      answer: null,
      answer_status: "unanswered",
      is_weak: false,
      is_bookmarked: false,
      timing: null,
      voice_transcript: [],
      audio_recording_available: false,
      practice_revision: null,
    },
  ],
  voice_disclaimer: "Text transcript only.",
  audio_playback_supported: false,
  audio_retention_policy: "No audio stored.",
  text_transcript_disclaimer: "Text only.",
};

afterEach(() => {
  cleanup();
});

describe("InterviewTranscriptReviewView", () => {
  it("filters items by search query", () => {
    const onChange = vi.fn();
    render(
      <InterviewTranscriptReviewView
        sessionId="sess1"
        review={review}
        onReviewChange={onChange}
      />
    );
    expect(screen.getAllByText(/leadership moment/i).length).toBeGreaterThan(0);

    const search = screen.getByLabelText(/search transcript/i);
    fireEvent.change(search, { target: { value: "Redis" } });

    const timeline = screen.getByRole("navigation", { name: /question timeline/i });
    expect(within(timeline).getByText(/Explain Redis caching/i)).toBeInTheDocument();
    expect(within(timeline).queryByText(/leadership moment/i)).toBeNull();
    expect(screen.getAllByRole("article")).toHaveLength(1);
  });

  it("shows audio playback unsupported messaging", () => {
    render(
      <InterviewTranscriptReviewView
        sessionId="sess1"
        review={review}
        onReviewChange={vi.fn()}
      />
    );
    expect(screen.getByText(/No audio stored/i)).toBeInTheDocument();
  });
});
