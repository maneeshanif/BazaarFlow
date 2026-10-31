const KEY = "bazaarflow-intro-seen";
let cached: boolean | undefined;

/**
 * Whether the opening plays on this visit: first page of a browser session, motion allowed. Decided once, on first
 * ask, so the opening and the hero (which waits for it) always agree even after the opening has marked itself seen.
 */
export function introWillPlay(): boolean {
  if (cached === undefined) {
    try {
      cached = window.sessionStorage.getItem(KEY) !== "1" && !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    } catch {
      cached = false; // storage blocked: skip the opening rather than repeat it on every page
    }
  }
  return cached;
}

export function markIntroSeen(): void {
  try {
    window.sessionStorage.setItem(KEY, "1");
  } catch {
    /* ignore */
  }
}

/** Seconds from the start of the opening until the hero may begin to animate. */
export const INTRO_SECONDS = 2.1;
