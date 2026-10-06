import { z } from "zod";
import { normalizePhone } from "@/lib/validation/register";

/** Client-side mirror of the voice settings rules (PRD F-023) for instant feedback. The API stays authoritative. */
export const voiceSettingsSchema = z.object({
  enabled: z.boolean(),
  greeting: z.string().trim().min(2, "Write a short greeting").max(200, "The greeting can be at most 200 characters"),
  consent_notice: z.string().trim().min(10, "The recording notice needs at least 10 characters").max(300, "The notice can be at most 300 characters"),
  max_call_seconds: z.coerce.number().int("Use a whole number").min(60, "At least 60 seconds").max(900, "At most 900 seconds"),
  monthly_cap_usd: z
    .string()
    .trim()
    .regex(/^\d{1,3}(\.\d{1,2})?$/, "Enter an amount like 5 or 5.50")
    .refine((v) => Number(v) <= 500, "At most $500"),
  handoff_phone: z
    .string()
    .trim()
    .transform((v) => (v === "" || v === "+92" ? "" : normalizePhone(v)))
    .pipe(z.string().regex(/^(\+[1-9][0-9]{7,14})?$/, "Enter a phone number like 0300 1234567")),
  retention_days: z.coerce.number().int("Use a whole number").min(1, "At least 1 day").max(365, "At most 365 days"),
});
