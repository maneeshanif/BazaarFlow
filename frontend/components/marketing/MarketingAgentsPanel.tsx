"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth/AuthProvider";

const AGENTS = [
  {
    key: "marketing",
    name: "Marketing agent",
    line: "Drafts picture posts, keeps the schedule and proposes comment replies. You approve each one.",
    href: "/marketing",
    action: "Open the studio",
    soon: false,
  },
  {
    key: "ads",
    name: "Facebook ads agent",
    line: "Will propose ad campaigns, budgets and audiences for your Page, and report what they earned. Coming next, once the Facebook account is connected.",
    href: "/marketing/ads",
    action: "See the plan",
    soon: true,
  },
] as const;

/** The two marketing agents, side by side, for the dashboards. Owners and managers only: staff cannot open marketing. */
export function MarketingAgentsPanel() {
  const { role } = useAuth();
  if (role !== "owner" && role !== "manager") return null;
  return (
    <section aria-label="Marketing agents" className="grid gap-5 md:grid-cols-2">
      {AGENTS.map((a) => (
        <div key={a.key} className="flex flex-col items-start gap-3 rounded-card border-2 border-line-strong bg-surface-raised p-6 shadow-card">
          <div className="flex items-center gap-3">
            <h2 className="text-ui-md font-semibold text-fg">{a.name}</h2>
            {a.soon ? <span className="rounded-pill bg-sunny px-3 py-0.5 text-ui-xs font-medium text-forest-ink">Coming next</span> : null}
          </div>
          <p className="max-w-prose text-ui-sm text-fg-muted">{a.line}</p>
          <Link href={a.href} className="text-ui-sm font-medium text-action hover:underline">
            {a.action}
          </Link>
        </div>
      ))}
    </section>
  );
}
