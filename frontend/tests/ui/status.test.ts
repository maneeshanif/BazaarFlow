import { describe, expect, it } from "vitest";
import { toneFor } from "@/lib/status";

describe("status -> tone (context/ui-tokens.md: a status means the same on every screen)", () => {
  it.each([
    ["posted", "success"], ["paid", "success"], ["connected", "success"], ["executed", "success"], ["approved", "success"],
    ["pending", "warning"], ["draft", "neutral"], ["scheduled", "info"],
    ["reversed", "danger"], ["rejected", "danger"], ["error", "danger"], ["failed", "danger"], ["expired", "danger"],
    ["ai_handling", "accent"], ["needs_human", "warning"], ["resolved", "neutral"],
  ])("%s is %s", (status, tone) => {
    expect(toneFor(status)).toBe(tone);
  });
  it("is case and separator insensitive, and neutral for unknown statuses", () => {
    expect(toneFor("Needs Human")).toBe("warning");
    expect(toneFor("something-new")).toBe("neutral");
  });
});
