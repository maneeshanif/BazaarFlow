import { describe, expect, it } from "vitest";
import { facebookSchema, onboardingShopSchema, replySchema, scheduleSchema, twilioSchema } from "@/lib/validation/channels";

const sid = "AC" + "a".repeat(32);
const schedule = { enabled: true, goal: "general", notes: "", tone: "friendly", language: "english", posts_per_day: 2, window_start: "10:00", window_end: "20:00", approval_mode: "manual" };

describe("integration credentials", () => {
  it("accepts a real-looking Twilio SID and token", () => {
    expect(twilioSchema.safeParse({ account_sid: sid, auth_token: "t".repeat(32) }).success).toBe(true);
  });
  it("rejects a malformed SID or a short token", () => {
    expect(twilioSchema.safeParse({ account_sid: "nope", auth_token: "t".repeat(32) }).success).toBe(false);
    expect(twilioSchema.safeParse({ account_sid: sid, auth_token: "short" }).success).toBe(false);
  });
  it("checks the Facebook page id and token", () => {
    expect(facebookSchema.safeParse({ page_id: "1234567890", access_token: "x".repeat(40) }).success).toBe(true);
    expect(facebookSchema.safeParse({ page_id: "abc", access_token: "x".repeat(40) }).success).toBe(false);
    expect(facebookSchema.safeParse({ page_id: "1234567890", access_token: "short" }).success).toBe(false);
  });
});

describe("schedule", () => {
  it("accepts a normal schedule", () => expect(scheduleSchema.safeParse(schedule).success).toBe(true));
  it("limits posts per day to 1 through 5", () => {
    expect(scheduleSchema.safeParse({ ...schedule, posts_per_day: 0 }).success).toBe(false);
    expect(scheduleSchema.safeParse({ ...schedule, posts_per_day: 6 }).success).toBe(false);
    expect(scheduleSchema.safeParse({ ...schedule, posts_per_day: 1.5 }).success).toBe(false);
  });
  it("needs the window to end after it starts", () => {
    expect(scheduleSchema.safeParse({ ...schedule, window_start: "20:00", window_end: "10:00" }).success).toBe(false);
    expect(scheduleSchema.safeParse({ ...schedule, window_start: "10:00", window_end: "10:00" }).success).toBe(false);
  });
});

describe("onboarding shop and reply", () => {
  it("turns a local phone into E.164 and checks the name", () => {
    const ok = onboardingShopSchema.safeParse({ name: "Ali Mart", owner_phone: "0300 1234567", city: "" });
    expect(ok.success && ok.data.owner_phone).toBe("+923001234567");
    expect(onboardingShopSchema.safeParse({ name: "a", owner_phone: "0300 1234567", city: "" }).success).toBe(false);
    expect(onboardingShopSchema.safeParse({ name: "Ali Mart", owner_phone: "abc", city: "" }).success).toBe(false);
  });
  it("needs a reply of 1 to 1000 characters", () => {
    expect(replySchema.safeParse({ text: "   " }).success).toBe(false);
    expect(replySchema.safeParse({ text: "x".repeat(1001) }).success).toBe(false);
    expect(replySchema.safeParse({ text: "Yes, come by" }).success).toBe(true);
  });
});
