import { z } from "zod";

export { fieldErrorsOf } from "@/lib/validation/common";

/**
 * Client-side mirror of the product rules (PRD F-010) for instant feedback only. The API stays authoritative:
 * contracts/invalid-product-inputs.json is read by both test suites so the two sides reject the same inputs.
 */

const money = z
  .string()
  .trim()
  .regex(/^\d{1,12}(\.\d{1,2})?$/, "Enter an amount like 2500 or 2500.50");

const optionalMoney = z
  .string()
  .trim()
  .transform((v) => (v === "" ? undefined : v))
  .pipe(money.optional());

const whole = (label: string) =>
  z.coerce
    .number({ invalid_type_error: `${label} must be a whole number` })
    .int(`${label} must be a whole number`)
    .min(0, `${label} cannot be negative`)
    .max(1_000_000, `${label} is too large`);

export const productSchema = z.object({
  sku: z.string().trim().min(1, "SKU is required").max(40, "SKU can be at most 40 characters"),
  name: z.string().trim().min(2, "Name needs at least 2 characters").max(120, "Name can be at most 120 characters"),
  category: z.string().trim().max(60, "Category can be at most 60 characters").optional(),
  price: money,
  cost: optionalMoney,
  qty_on_hand: whole("Quantity"),
  reorder_level: whole("Reorder level").optional(),
  vendor_id: z.string().uuid().optional(),
  active: z.boolean().default(true),
});

export type ProductInput = z.input<typeof productSchema>;

export const stockMovementSchema = z.object({
  delta: z.coerce
    .number({ invalid_type_error: "Enter a whole number" })
    .int("Enter a whole number")
    .refine((n) => n !== 0, "Enter a number other than zero")
    .refine((n) => Math.abs(n) <= 1_000_000, "That quantity is too large"),
  reason: z.enum(["purchase", "adjustment", "return"]),
  note: z.string().trim().max(255, "Note can be at most 255 characters").optional(),
});
