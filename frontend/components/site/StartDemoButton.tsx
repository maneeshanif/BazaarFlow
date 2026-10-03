"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { SITE_PRIMARY } from "@/components/site/styles";
import { cn } from "@/lib/utils";

/**
 * Starts the visitor's own temporary demo shop (PRD F-027) and opens it. The server answers with the session in an
 * httpOnly cookie; the app's own provider restores it from there when the dashboard loads.
 */
export function StartDemoButton({ className, children = "Try the live demo" }: { className?: string; children?: React.ReactNode }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    if (busy) return; // one shop per click, even for a double click
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/demo/start", { method: "POST", credentials: "same-origin", signal: AbortSignal.timeout(75_000) });
      if (res.ok) {
        router.push("/dashboard");
        return; // stays disabled while the page changes
      }
      const body = await res.json().catch(() => ({}));
      setError(typeof body?.detail === "string" ? body.detail : "Could not start the demo. Try again.");
    } catch {
      setError("Could not reach the server. Check your connection and try again.");
    }
    setBusy(false);
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <button type="button" onClick={() => void start()} disabled={busy} aria-busy={busy} className={cn(SITE_PRIMARY, className)}>
        {busy ? "Setting up your shop..." : children}
      </button>
      {error ? (
        <p role="alert" className="max-w-prose rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
          {error}
        </p>
      ) : null}
    </div>
  );
}
