import { NextRequest, NextResponse } from "next/server";
import { callBackend, publicSession, setRefreshCookie, unreachable, type BackendTokens } from "@/lib/auth/server";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  let body: { email?: unknown; password?: unknown; tenant_id?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "Invalid request" }, { status: 400 });
  }
  if (typeof body.email !== "string" || typeof body.password !== "string") {
    return NextResponse.json({ detail: "Email and password are required" }, { status: 400 });
  }

  let upstream: Response;
  try {
    upstream = await callBackend("/api/v1/auth/login", {
      email: body.email,
      password: body.password,
      ...(typeof body.tenant_id === "string" ? { tenant_id: body.tenant_id } : {}),
    });
  } catch {
    return unreachable();
  }

  const payload = await upstream.json().catch(() => ({ detail: "Unexpected response" }));
  if (!upstream.ok) {
    // wrong password, lockout (429), tenant choice (409): the backend's message is safe to show
    return NextResponse.json(payload, { status: upstream.status });
  }
  const res = NextResponse.json(publicSession(payload as BackendTokens));
  setRefreshCookie(res, (payload as BackendTokens).refresh_token);
  return res;
}
