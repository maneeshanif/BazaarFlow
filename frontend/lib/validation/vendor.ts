import { z } from "zod";
import { normalizePhone } from "@/lib/validation/register";

/**
 * Client-side mirror of the vendor, bill and payment rules (PRD F-012) for instant feedback. The API stays
 * authoritative (the same limits, plus "no more than you owe" which depends on the live balance).
 */

const money = z
  .string()
  .trim()
  .regex(/^\d{1,12}(\.\d{1,2})?$/, "Enter an amount like 500 or 500.50")
  .refine((v) => Number(v) > 0, "Enter an amount above zero");

export const vendorSchema = z.object({
  name: z.string().trim().min(2, "Name needs at least 2 characters").max(120, "Name can be at most 120 characters"),
  phone: z
    .string()
    .transform((v) => (v.trim() === "" || v.trim() === "+92" ? "" : normalizePhone(v)))
    .pipe(z.string().regex(/^(\+?[0-9]{7,20})?$/, "Enter a phone number like 0300 1234567")),
});

export const billSchema = z.object({
  amount: money,
  due_date: z
    .string()
    .trim()
    .refine((v) => v === "" || /^\d{4}-\d{2}-\d{2}$/.test(v), "Pick a date"),
  reference: z.string().trim().max(60, "Reference can be at most 60 characters"),
  note: z.string().trim().max(255, "Note can be at most 255 characters"),
});

export const vendorPaymentSchema = z.object({
  amount: money,
  method: z.enum(["cash", "card", "bank", "wallet"]),
});
