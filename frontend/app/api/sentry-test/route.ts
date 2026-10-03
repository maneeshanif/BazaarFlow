import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export function GET() {
  // ⚠️ TEMPORARY: Sentry verification error — DELETE after confirming in Sentry
  throw new Error("Sentry test error — BazaarFlow frontend ✅");
  return NextResponse.json({ ok: true });
}
