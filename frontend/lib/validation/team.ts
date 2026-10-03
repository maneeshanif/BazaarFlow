import { z } from "zod";

/**
 * Client-side mirror of the team rules (PRD F-019) for instant feedback; the API stays authoritative (it also refuses
 * common passwords and says when a new person still needs a first password).
 */
export const teamMemberSchema = z.object({
  name: z.string().trim().min(2, "Name needs at least 2 characters").max(80, "Name can be at most 80 characters"),
  email: z
    .string()
    .trim()
    .min(1, "Enter their email")
    .max(254, "Email can be at most 254 characters")
    .email("Enter an email like name@example.com"),
  role: z.enum(["manager", "staff"], { errorMap: () => ({ message: "Choose what they can do" }) }),
  password: z
    .string()
    .refine((v) => v === "" || v.length >= 8, "Password must be at least 8 characters")
    .refine((v) => v.length <= 128, "Password can be at most 128 characters")
    .optional(),
});
