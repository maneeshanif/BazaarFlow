import { NextRequest, NextResponse } from "next/server";
import {
  REFRESH_COOKIE,
  callBackend,
  clearRefreshCookie,
  isSession,
  publicSession,
  setRefreshCookie,
  unreachable,
} from "@/lib/auth/server";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;
  if (!refreshToken) return NextResponse.json({ detail: "No session" }, { status: 401 });

  let upstream: Response;
  try {
    upstream = await callBackend("/api/v1/auth/refresh", { refresh_token: refreshToken });
  } catch {
    return unreachable();
  }
  if (upstream.status === 400 || upstream.status === 401 || upstream.status === 403) {
    // the token is really dead (expired, revoked, reused): end the session
    const res = NextResponse.json({ detail: "Session expired" }, { status: 401 });
    clearRefreshCookie(res);
    return res;
  }
  const tokens: unknown = upstream.ok ? await upstream.json().catch(() => null) : null;
  if (!isSession(tokens)) {
    // a restart, rate limit or bad gateway is transient: keep the cookie so the next attempt can succeed
    return NextResponse.json({ detail: "Temporarily unavailable" }, { status: upstream.ok ? 502 : 503 });
  }
  const res = NextResponse.json(publicSession(tokens));
  setRefreshCookie(res, tokens.refresh_token); // rotated: the old one is now dead
  return res;
}
