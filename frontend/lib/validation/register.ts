import { z } from "zod";

/**
 * Client-side mirror of the account rules (PRD F-002) for instant feedback. The API stays authoritative: it also
 * refuses common passwords, duplicate emails and sign-up floods, and its messages are shown under the same fields.
 */

/** "0300 1234567" -> "+923001234567" (the form defaults to Pakistan); an international "+44 ..." number is kept. */
export function normalizePhone(input: string): string {
  let value = input.replace(/[\s\-().]/g, "");
  if (value.startsWith("00")) value = `+${value.slice(2)}`;
  else if (value.startsWith("0")) value = `+92${value.slice(1)}`;
  else if (value.startsWith("92") && !value.startsWith("+")) value = `+${value}`;
  return value;
}

const person = (label: string) =>
  z
    .string()
    .trim()
    .min(2, `${label} needs at least 2 characters`)
    .max(80, `${label} can be at most 80 characters`);

export const registerSchema = z.object({
  full_name: person("Your name"),
  email: z
    .string()
    .trim()
    .min(1, "Enter your email")
    .max(254, "Email can be at most 254 characters")
    .email("Enter an email like name@example.com"),
  password: z.string().min(8, "Password must be at least 8 characters").max(128, "Password can be at most 128 characters"),
  shop_name: person("Shop name"),
  phone: z
    .string()
    .transform(normalizePhone)
    .pipe(z.string().regex(/^\+[1-9][0-9]{7,14}$/, "Enter a phone number like 0300 1234567 or +92 300 1234567")),
  city: z.string().trim().max(60, "City can be at most 60 characters").optional(),
  accept_terms: z.literal(true, { errorMap: () => ({ message: "You need to accept the terms to create an account" }) }),
});

export type RegisterFormInput = z.input<typeof registerSchema>;
