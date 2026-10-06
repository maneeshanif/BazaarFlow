import { describe, expect, it } from "vitest";
import { voiceSettingsSchema } from "@/lib/validation/voice";

const ok = { enabled: true, greeting: "Hello", consent_notice: "This call may be recorded.", max_call_seconds: "300", monthly_cap_usd: "5.00", handoff_phone: "", retention_days: "30" };

describe("voiceSettingsSchema (PRD F-023)", () => {
  it("accepts normal settings and turns a local handoff phone into E.164", () => {
    expect(voiceSettingsSchema.safeParse(ok).success).toBe(true);
    const parsed = voiceSettingsSchema.safeParse({ ...ok, handoff_phone: "0300 1234567" });
    expect(parsed.success && parsed.data.handoff_phone).toBe("+923001234567");
  });
  it("needs a real recording notice", () => {
    expect(voiceSettingsSchema.safeParse({ ...ok, consent_notice: "short" }).success).toBe(false);
  });
  it("limits the call length, budget and retention", () => {
    expect(voiceSettingsSchema.safeParse({ ...ok, max_call_seconds: "59" }).success).toBe(false);
    expect(voiceSettingsSchema.safeParse({ ...ok, max_call_seconds: "901" }).success).toBe(false);
    expect(voiceSettingsSchema.safeParse({ ...ok, monthly_cap_usd: "-1" }).success).toBe(false);
    expect(voiceSettingsSchema.safeParse({ ...ok, monthly_cap_usd: "501" }).success).toBe(false);
    expect(voiceSettingsSchema.safeParse({ ...ok, retention_days: "0" }).success).toBe(false);
    expect(voiceSettingsSchema.safeParse({ ...ok, retention_days: "366" }).success).toBe(false);
  });
  it("rejects a malformed handoff phone", () => {
    expect(voiceSettingsSchema.safeParse({ ...ok, handoff_phone: "abc" }).success).toBe(false);
  });
});
