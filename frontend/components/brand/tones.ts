/** The five product colours of the identity (docs/design/reference-sweettape/tokens.md). */
export type Tone = "lime" | "coral" | "orange" | "sunny" | "sky" | "indigo" | "forest" | "cream";

/** Background and text classes per tone; every pair is an identity colour on its ink, all tokens. */
export const TONE_CLASS: Record<Tone, string> = {
  lime: "bg-lime text-forest-ink",
  coral: "bg-coral text-forest-ink",
  orange: "bg-orange text-forest-ink",
  sunny: "bg-sunny text-forest-ink",
  sky: "bg-sky text-forest-ink",
  indigo: "bg-indigo text-cream",
  forest: "bg-forest text-lime",
  cream: "bg-cream text-forest-ink",
};
