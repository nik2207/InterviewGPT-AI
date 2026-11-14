import { describe, expect, it } from "vitest";

import { isSpeechSynthesisSupported } from "@/lib/speech/useSpeechSynthesis";

describe("useSpeechSynthesis", () => {
  it("detects speech synthesis in test environment", () => {
    expect(typeof isSpeechSynthesisSupported()).toBe("boolean");
  });
});
