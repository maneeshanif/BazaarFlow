import { NextRequest, NextResponse } from "next/server";
import {
  REFRESH_COOKIE,
  callBackend,
  clearRefreshCookie,
  publicSession,
  setRefreshCookie,
  unreachable,
  type BackendTokens,
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
  if (!upstream.ok) {
    const res = NextResponse.json({ detail: "Session expired" }, { status: 401 });
    clearRefreshCookie(res);
    return res;
  }
  const tokens = (await upstream.json()) as BackendTokens;
  const res = NextResponse.json(publicSession(tokens));
  setRefreshCookie(res, tokens.refresh_token); // rotated: the old one is now dead
  return res;
}
