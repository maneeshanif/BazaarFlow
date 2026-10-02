import { NextResponse } from "next/server";

/**
 * Server-side helpers for the auth route handlers (the BFF in front of the FastAPI backend).
 * The refresh token lives in an httpOnly cookie scoped to /api/auth, so page JavaScript can never read it.
 */
export const REFRESH_COOKIE = "bf_refresh";
const COOKIE_PATH = "/api/auth";
const REFRESH_DAYS = 14;

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

export async function callBackend(path: string, body: unknown): Promise<Response> {
  return fetch(backendUrl(path), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
}

export const unreachable = () => NextResponse.json({ detail: "The service is temporarily unavailable." }, { status: 502 });
