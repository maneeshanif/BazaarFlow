import { describe, expect, it } from "vitest";
import { shopSettingsSchema } from "@/lib/validation/shop";

const ok = { name: "Ali Mart", owner_phone: "0300 1234567", city: "Lahore", auto_post_limit: "" };

describe("shopSettingsSchema (PRD F-020)", () => {
  it("accepts a normal profile and turns a local phone into E.164", () => {
    const parsed = shopSettingsSchema.safeParse(ok);
    expect(parsed.success).toBe(true);
    if (parsed.success) expect(parsed.data.owner_phone).toBe("+923001234567");
  });
  it("checks the shop name length", () => {
    expect(shopSettingsSchema.safeParse({ ...ok, name: "a" }).success).toBe(false);
    expect(shopSettingsSchema.safeParse({ ...ok, name: "n".repeat(81) }).success).toBe(false);
  });
  it("needs a valid phone and a city of at most 60 characters", () => {
    expect(shopSettingsSchema.safeParse({ ...ok, owner_phone: "abc" }).success).toBe(false);
    expect(shopSettingsSchema.safeParse({ ...ok, city: "c".repeat(61) }).success).toBe(false);
  });
  it("accepts an empty or positive money limit only", () => {
    expect(shopSettingsSchema.safeParse({ ...ok, auto_post_limit: "2000" }).success).toBe(true);
    expect(shopSettingsSchema.safeParse({ ...ok, auto_post_limit: "2000.50" }).success).toBe(true);
    expect(shopSettingsSchema.safeParse({ ...ok, auto_post_limit: "-1" }).success).toBe(false);
    expect(shopSettingsSchema.safeParse({ ...ok, auto_post_limit: "1.234" }).success).toBe(false);
    expect(shopSettingsSchema.safeParse({ ...ok, auto_post_limit: "20000000" }).success).toBe(false);
  });
});
