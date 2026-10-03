import { NextRequest, NextResponse } from "next/server";
import { callBackend, isSession, publicSession, setRefreshCookie, unreachable } from "@/lib/auth/server";

export const dynamic = "force-dynamic";

const FIELDS = ["full_name", "email", "password", "shop_name", "phone", "city", "accept_terms"] as const;

/**
 * Create the account and the shop, then keep the session exactly as sign-in does: the refresh token goes into an
 * httpOnly cookie and the browser only receives the access token. The visitor's address is forwarded so the API's
 * per-address sign-up limit counts visitors, not this server.
 */
export async function POST(request: NextRequest) {
  let body: Record<string, unknown>;
  try {
    const parsed: unknown = await request.json();
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("not an object");
    body = parsed as Record<string, unknown>;
  } catch {
    return NextResponse.json({ detail: "Invalid request" }, { status: 400 });
  }

  const forward: Record<string, unknown> = {};
  for (const key of FIELDS) if (key in body) forward[key] = body[key];

  let upstream: Response;
  try {
    upstream = await callBackend("/api/v1/auth/register", forward, {
      "x-forwarded-for": request.headers.get("x-forwarded-for") ?? "",
    });
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
