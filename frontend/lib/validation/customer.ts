import { z } from "zod";
import { normalizePhone } from "@/lib/validation/register";

/**
 * Client-side mirror of the customer and payment rules (PRD F-009) for instant feedback. The API stays authoritative
 * (the same limits, plus "no more than they owe" which depends on the live balance).
 */

export const customerSchema = z.object({
  phone: z
    .string()
    .transform(normalizePhone)
    .pipe(z.string().regex(/^\+?[0-9]{7,20}$/, "Enter a phone number like 0300 1234567")),
  name: z.string().trim().max(255, "Name can be at most 255 characters").optional(),
  email: z
    .string()
    .trim()
    .max(254, "Email can be at most 254 characters")
    .refine((v) => v === "" || z.string().email().safeParse(v).success, "Enter an email like name@example.com")
    .optional(),
  address: z.string().trim().max(512, "Address can be at most 512 characters").optional(),
});

export const paymentSchema = z.object({
  amount: z
    .string()
    .trim()
    .regex(/^\d{1,12}(\.\d{1,2})?$/, "Enter an amount like 500 or 500.50")
    .refine((v) => Number(v) > 0, "Enter an amount above zero"),
  method: z.enum(["cash", "card", "bank", "wallet"]),
});
