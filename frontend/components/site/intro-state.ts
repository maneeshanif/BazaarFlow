const KEY = "bazaarflow-intro-seen";

/** Seconds from the start of the opening until the hero may begin to animate (the CSS delays use the same number). */
export const INTRO_SECONDS = 2.4;
/** Seconds until the opening has fully gone. */
export const INTRO_TOTAL_SECONDS = 3.3;

/**
 * Runs before the first paint (an inline script in the public layout). On the first page of a browser session, with motion
 * allowed, it puts `data-intro` on <html>: the CSS then shows the opening and delays the hero by the opening's length, from
 * the very first frame, so nothing flashes before the opening starts. Storage blocked means no opening, rather than one on
 * every page.
 */
export const INTRO_BOOT_SCRIPT = `try{if(sessionStorage.getItem("${KEY}")!=="1"&&!matchMedia("(prefers-reduced-motion: reduce)").matches)document.documentElement.dataset.intro="1"}catch(e){}`;

export function markIntroSeen(): void {
  try {
    window.sessionStorage.setItem(KEY, "1");
  } catch {
    /* ignore */
  }
}
