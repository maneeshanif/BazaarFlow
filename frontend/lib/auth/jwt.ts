/**
 * Token helpers. The browser never trusts a token: it only reads `exp` to know when to refresh. The backend
 * re-validates the user, tenant and role against the database on every request.
 */

export function decodeExp(token: string): number | null {
  const part = token.split(".")[1];
  if (!part) return null;
  try {
    const base64 = part.replace(/-/g, "+").replace(/_/g, "/");
    const json = typeof atob === "function" ? atob(base64) : Buffer.from(base64, "base64").toString("utf8");
    const exp = (JSON.parse(json) as { exp?: unknown }).exp;
    return typeof exp === "number" ? exp : null;
  } catch {
    return null;
  }
}

const MIN_DELAY_MS = 5_000;
const UNKNOWN_EXPIRY_RETRY_MS = 30_000;

/**
 * Milliseconds until the access token should be refreshed: one minute before it expires, but never sooner than
 * 5 seconds (a very short-lived token must not cause a refresh loop) and, if the expiry cannot be read, 30 seconds.
 */
export function msUntilRefresh(token: string, now: number = Date.now(), skewMs = 60_000): number {
  const exp = decodeExp(token);
  if (exp === null) return UNKNOWN_EXPIRY_RETRY_MS;
  return Math.max(MIN_DELAY_MS, exp * 1000 - now - skewMs);
}

/** A post-sign-in destination is accepted only if it is a path on this site (no open redirects). */
export function safeNextPath(value: string | null | undefined): string | null {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\") || value.includes("://")) {
    return null;
  }
  return value;
}
