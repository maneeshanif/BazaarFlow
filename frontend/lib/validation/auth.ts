import { z } from "zod";

/**
 * Client-side mirror of the sign-in rules (PRD F-001) for instant feedback. The API stays authoritative and answers
 * the same invalid input with 422; a wrong password is always the same 401 so nothing reveals which part was wrong.
 */
export const signInSchema = z.object({
  email: z
    .string()
    .trim()
    .min(1, "Enter your email")
    .max(254, "Email can be at most 254 characters")
    .email("Enter an email like name@example.com"),
  password: z.string().min(8, "Password must be at least 8 characters").max(128, "Password can be at most 128 characters"),
});

export type SignInInput = z.input<typeof signInSchema>;
