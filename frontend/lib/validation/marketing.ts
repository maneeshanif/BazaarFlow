import { z } from "zod";

/**
 * Client-side mirror of the marketing studio rules (PRD F-014) for instant feedback; the API stays authoritative
 * (contracts: app/schemas/marketing_studio.py).
 */
export const briefSchema = z
  .object({
    goal: z.enum(["promote_product", "announce_offer", "festival_greeting", "general"], { errorMap: () => ({ message: "Choose what the post is for" }) }),
    tone: z.enum(["friendly", "professional", "festive"]),
    language: z.enum(["english", "roman_urdu"]),
    productId: z.string(),
    notes: z.string().trim().max(300, "Notes can be at most 300 characters"),
  })
  .refine((v) => v.goal !== "promote_product" || v.productId !== "", { path: ["productId"], message: "Choose the product to promote" });

const HASHTAG = /^#[A-Za-z0-9_]{2,40}$/;

export function normaliseHashtags(raw: string): string {
  return raw
    .split(/\s+/)
    .filter(Boolean)
    .map((t) => (t.startsWith("#") ? t : `#${t}`))
    .slice(0, 10)
    .join(" ");
}

export const postSchema = z.object({
  title: z.string().trim().min(1, "Give the post a title").max(120, "The title can be at most 120 characters"),
  message: z.string().trim().min(1, "Write the message").max(1000, "The message can be at most 1000 characters"),
  hashtags: z
    .string()
    .max(300, "Hashtags can be at most 300 characters")
    .refine((v) => normaliseHashtags(v).split(/\s+/).filter(Boolean).every((t) => HASHTAG.test(t)), "Hashtags use letters, numbers and underscores only"),
});
