import { NextRequest, NextResponse } from "next/server";
import { callBackend, isSession, publicSession, setRefreshCookie, unreachable } from "@/lib/auth/server";

export const dynamic = "force-dynamic";

/**
 * Start the visitor's own temporary demo shop and keep the session exactly as sign-in does: the refresh token goes
 * into an httpOnly cookie and the browser only receives the access token. The visitor's address is forwarded so the
 * API's per-address demo limit counts visitors, not this server.
 */
export async function POST(request: NextRequest) {
  let upstream: Response;
  try {
    upstream = await callBackend("/api/v1/demo/start", {}, { "x-forwarded-for": request.headers.get("x-forwarded-for") ?? "" }, 60_000); // the shop is filled with data on the way in
  } catch {
    return unreachable();
  }
  const payload = await upstream.json().catch(() => ({ detail: "Unexpected response" }));
  if (!upstream.ok) return NextResponse.json(payload, { status: upstream.status });
  if (!isSession(payload)) return unreachable();
  const res = NextResponse.json(publicSession(payload), { status: 201 });
  setRefreshCookie(res, payload.refresh_token);
  return res;
}
