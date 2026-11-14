import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React, { useCallback, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SpeechAnswerInput } from "@/components/interviews/SpeechAnswerInput";
import type { InputMode, SpeechMetrics } from "@/lib/speech/metrics";
import { metricsReportKey } from "@/lib/speech/metricsReport";

vi.mock("@/lib/speech/useSpeechRecognition", () => ({
  useSpeechRecognition: () => ({
    supported: false,
    permissionState: "unsupported",
    errorMessage: null,
    durationSeconds: null,
    start: vi.fn(),
    stop: vi.fn(),
  }),
}));

function Harness({
  onMetricsSpy,
}: {
  onMetricsSpy: (metrics: SpeechMetrics, mode: InputMode) => void;
}) {
  const [value, setValue] = useState("");
  const onMetricsChange = useCallback(onMetricsSpy, [onMetricsSpy]);
  return (
    <SpeechAnswerInput
      value={value}
      onChange={setValue}
      onMetricsChange={onMetricsChange}
    />
  );
}

afterEach(() => {
  cleanup();
});

describe("SpeechAnswerInput", () => {
  it("does not loop parent updates on mount", () => {
    const spy = vi.fn();
    render(<Harness onMetricsSpy={spy} />);
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it("updates answer text when typing", () => {
    const spy = vi.fn();
    render(<Harness onMetricsSpy={spy} />);
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "Hello" } });
    fireEvent.change(textarea, { target: { value: "Hello world" } });
    expect(textarea).toHaveValue("Hello world");
  });

  it("notifies parent when word count changes, not on identical metrics", () => {
    const spy = vi.fn();
    render(<Harness onMetricsSpy={spy} />);
    const initialCalls = spy.mock.calls.length;
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "one two three" } });
    expect(spy.mock.calls.length).toBeGreaterThan(initialCalls);
    const lastCall = spy.mock.calls.at(-1);
    expect(lastCall?.[0].word_count).toBe(3);

    const keyAfter = metricsReportKey(lastCall![0], lastCall![1]);
    expect(keyAfter).toBeTruthy();
  });
});
