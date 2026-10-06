import { z } from "zod";
import { normalizePhone } from "@/lib/validation/register";

/** Client-side mirror of the shop profile rules (PRD F-020) for instant feedback. The API stays authoritative. */

export const shopSettingsSchema = z.object({
  name: z.string().trim().min(2, "Shop name needs at least 2 characters").max(80, "Shop name can be at most 80 characters"),
  owner_phone: z
    .string()
    .transform(normalizePhone)
    .pipe(z.string().regex(/^\+[1-9][0-9]{7,14}$/, "Enter a phone number like 0300 1234567 or +92 300 1234567")),
  city: z.string().trim().max(60, "City can be at most 60 characters"),
  /** empty means "use the default": the AI always asks first */
  auto_post_limit: z
    .string()
    .trim()
    .refine((v) => v === "" || /^\d{1,8}(\.\d{1,2})?$/.test(v), "Enter an amount like 2000 or 2000.50, or leave it empty")
    .refine((v) => v === "" || Number(v) <= 10_000_000, "The limit can be at most Rs 10,000,000"),
});
