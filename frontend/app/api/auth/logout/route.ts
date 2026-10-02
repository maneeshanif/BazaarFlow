import { NextRequest, NextResponse } from "next/server";
import { REFRESH_COOKIE, callBackend, clearRefreshCookie } from "@/lib/auth/server";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;
  if (refreshToken) {
    // best effort: the cookie is cleared even if the backend cannot be reached
    await callBackend("/api/v1/auth/logout", { refresh_token: refreshToken }).catch(() => undefined);
  }
  const res = new NextResponse(null, { status: 204 });
  clearRefreshCookie(res);
  return res;
}
