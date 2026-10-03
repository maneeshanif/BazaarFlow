import { NextResponse } from "next/server";

/**
 * Server-side helpers for the auth route handlers (the BFF in front of the FastAPI backend).
 * The refresh token lives in an httpOnly cookie scoped to /api/auth, so page JavaScript can never read it.
 */
export const REFRESH_COOKIE = "bf_refresh";
const COOKIE_PATH = "/api/auth";
const REFRESH_DAYS = 14;
const BACKEND_TIMEOUT_MS = 10_000;

export function backendUrl(path: string): string {
  const base = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  return `${base.replace(/\/$/, "")}${path}`;
}

export function setRefreshCookie(res: NextResponse, value: string): void {
  res.cookies.set(REFRESH_COOKIE, value, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: COOKIE_PATH,
    maxAge: REFRESH_DAYS * 24 * 60 * 60,
  });
}

export function clearRefreshCookie(res: NextResponse): void {
  res.cookies.set(REFRESH_COOKIE, "", {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: COOKIE_PATH,
    maxAge: 0,
  });
}

export type BackendTokens = { access_token: string; refresh_token: string; tenant_id: string; role: string };

/** What the browser is allowed to see: never the refresh token. */
export function publicSession(tokens: BackendTokens) {
  return { access_token: tokens.access_token, tenant_id: tokens.tenant_id, role: tokens.role };
}

/** A kept-alive connection that the API closed while idle: the request never reached it, so one retry is safe. */
function isStaleSocket(error: unknown): boolean {
  const cause = (error as { cause?: { code?: string; message?: string } } | null)?.cause;
  const text = `${(error as Error | null)?.message ?? ""} ${cause?.message ?? ""}`;
  return ["ECONNRESET", "UND_ERR_SOCKET", "EPIPE"].includes(cause?.code ?? "") || /socket hang up|other side closed/i.test(text);
}

export async function callBackend(path: string, body: unknown, extraHeaders: Record<string, string> = {}, timeoutMs: number = BACKEND_TIMEOUT_MS): Promise<Response> {
  const headers: Record<string, string> = { "content-type": "application/json" };
  for (const [key, value] of Object.entries(extraHeaders)) if (value) headers[key] = value;
  const send = () =>
    fetch(backendUrl(path), {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(timeoutMs), // a hung API must not hang the page
    });
  try {
    return await send();
  } catch (error) {
    if (isStaleSocket(error)) return send(); // once, and only for a reset connection (never for a timeout)
    throw error;
  }
}

/** True when the backend answered with a well-formed session (never trust a 200 blindly). */
export function isSession(value: unknown): value is BackendTokens {
  const v = value as Partial<BackendTokens> | null;
  return (
    !!v &&
    typeof v === "object" &&
    typeof v.access_token === "string" &&
    typeof v.refresh_token === "string" &&
    typeof v.tenant_id === "string" &&
    typeof v.role === "string"
  );
}

export const unreachable = () => NextResponse.json({ detail: "The service is temporarily unavailable." }, { status: 502 });
