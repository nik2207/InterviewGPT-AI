import { describe, expect, it } from "vitest";

import { buildSpeechMetrics } from "@/lib/speech/metrics";
import { metricsReportKey } from "@/lib/speech/metricsReport";

describe("metricsReportKey", () => {
  it("returns the same key for equivalent metrics", () => {
    const metrics = buildSpeechMetrics("hello world", "typed", null);
    const a = metricsReportKey(metrics, "typed");
    const b = metricsReportKey(
      buildSpeechMetrics("hello world", "typed", null),
      "typed"
    );
    expect(a).toBe(b);
  });

  it("changes when word count changes", () => {
    const first = metricsReportKey(
      buildSpeechMetrics("one", "typed", null),
      "typed"
    );
    const second = metricsReportKey(
      buildSpeechMetrics("one two", "typed", null),
      "typed"
    );
    expect(first).not.toBe(second);
  });
});
