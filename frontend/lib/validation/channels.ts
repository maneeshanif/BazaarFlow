import { z } from "zod";
import { normalizePhone } from "@/lib/validation/register";

/** Client-side mirrors of the integration, schedule and onboarding rules (PRD F-018, F-015, F-003) for instant feedback. */

export const twilioSchema = z.object({
  account_sid: z.string().trim().regex(/^AC[0-9a-fA-F]{32}$/, "The Account SID starts with AC and is 34 characters long"),
  auth_token: z.string().trim().min(16, "The Auth Token is at least 16 characters").max(64, "The Auth Token is at most 64 characters"),
});

export const facebookSchema = z.object({
  page_id: z.string().trim().regex(/^[0-9]{5,30}$/, "The Page id is a number of 5 to 30 digits"),
  access_token: z.string().trim().min(20, "Paste the full Page access token").max(600, "That token is too long"),
});

export const vapiSchema = z.object({
  assistant_id: z.string().trim().regex(/^[A-Za-z0-9_-]{8,64}$/, "The assistant id is 8 to 64 letters, numbers, dashes or underscores"),
  webhook_secret: z.string().trim().min(16, "The token is at least 16 characters").max(128, "The token is at most 128 characters"),
});

export const scheduleSchema = z
  .object({
    enabled: z.boolean(),
    goal: z.enum(["announce_offer", "festival_greeting", "general"]),
    notes: z.string().trim().max(300, "Notes can be at most 300 characters"),
    tone: z.enum(["friendly", "professional", "festive"]),
    language: z.enum(["english", "roman_urdu"]),
    posts_per_day: z.coerce.number().int("Use a whole number").min(1, "At least 1 post a day").max(5, "At most 5 posts a day"),
    window_start: z.string().regex(/^\d{2}:\d{2}$/, "Pick a time"),
    window_end: z.string().regex(/^\d{2}:\d{2}$/, "Pick a time"),
    approval_mode: z.enum(["manual", "auto"]),
  })
  .refine((v) => v.window_start < v.window_end, { path: ["window_end"], message: "The window must end after it starts" });

export const onboardingShopSchema = z.object({
  name: z.string().trim().min(2, "Shop name needs at least 2 characters").max(80, "Shop name can be at most 80 characters"),
  owner_phone: z
    .string()
    .transform(normalizePhone)
    .pipe(z.string().regex(/^\+[1-9][0-9]{7,14}$/, "Enter a phone number like 0300 1234567 or +92 300 1234567")),
  city: z.string().trim().max(60, "City can be at most 60 characters"),
});

export const replySchema = z.object({ text: z.string().trim().min(1, "Write a message").max(1000, "A message can be at most 1,000 characters") });
