"use client";

import Link from "next/link";
import { useState } from "react";
import { buttonClass } from "@/components/app/Button";
import { KpiCard } from "@/components/app/KpiCard";
import { PageHeader } from "@/components/app/PageHeader";
import { ErrorState } from "@/components/app/StateViews";
import { SelectInput } from "@/components/form/Controls";
import { Skeleton } from "@/components/ui/skeleton";
import { useLoad } from "@/hooks/useLoad";
import { apiGet } from "@/lib/api/client";
import type { AgentDashboard, DashboardRange } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";

const RANGES: { value: DashboardRange; label: string }[] = [
  { value: "today", label: "Today" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
];

const delta = (percent: number | null): string | undefined => (percent === null ? undefined : `${percent >= 0 ? "+" : "-"}${Math.abs(percent)}%`);

const hours = (minutes: number): string => {
  if (minutes < 60) return `${formatNumber(minutes)} min`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${formatNumber(h)} h` : `${formatNumber(h)} h ${m} min`;
};

/** The agent command center (PRD D-003) for owners and managers: what the AI did, how often people agreed, cost and time saved. */
export function AgentDashboardView() {
  const [range, setRange] = useState<DashboardRange>("7d");
  const loaded = useLoad(() => apiGet<AgentDashboard>("/agent-runs/dashboard", { range }), [range]);
  const data = loaded.data;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Agent command center" description="What your AI assistant did, and what it cost." />
      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-surface p-3" role="search" aria-label="Choose the period">
        <div className="flex flex-col gap-1">
          <label htmlFor="agent-range" className="text-ui-xs font-medium text-fg-muted">
            Period
          </label>
          <SelectInput id="agent-range" value={range} onChange={(e) => setRange(e.target.value as DashboardRange)}>
            {RANGES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </SelectInput>
        </div>
      </div>

      {loaded.state === "loading" && !data ? (
        <div role="status" aria-busy="true" aria-label="Loading the command center" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : null}
      {loaded.state === "error" ? <ErrorState message={loaded.error?.message ?? "Could not load the command center."} onRetry={loaded.reload} /> : null}
      {loaded.state === "unauthorized" ? <ErrorState message="Only owners and managers can open this page." /> : null}

      {data && data.is_empty ? (
        <section aria-label="Nothing to show yet" className="flex flex-col items-start gap-3 rounded-lg border border-border bg-surface p-4">
          <h2 className="text-ui-md font-semibold text-fg">Your assistant has not done anything yet</h2>
          <p className="max-w-prose text-ui-sm text-fg-muted">Ask it to record a sale or check your stock and its activity will show up here.</p>
          <Link href="/sales/chat" className={buttonClass("primary")}>
            Open sales chat
          </Link>
        </section>
      ) : null}

      {data && !data.is_empty ? (
        <>
          {!data.enabled ? (
            <p role="status" className="rounded-md border border-border bg-surface px-3 py-2 text-ui-sm text-fg">
              The AI assistant is switched off for your shop. Turn it on from the agent activity page.
            </p>
          ) : null}
          <section aria-label="Key figures" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <KpiCard label="Agent runs today" value={formatNumber(data.runs_today)} href="/agent-activity" />
            <KpiCard label="Runs in this period" value={formatNumber(data.runs.value)} delta={delta(data.runs.change_percent)} href="/agent-activity" />
            <KpiCard
              label="Approval rate"
              value={data.approval.rate_percent === null ? "No decisions yet" : `${data.approval.rate_percent}%`}
              href="/approvals"
            />
            <KpiCard label="Failed runs" value={formatNumber(data.failed_runs.value)} delta={delta(data.failed_runs.change_percent)} href="/agent-activity" />
            <KpiCard label="AI spend this month" value={`$${data.spend.month_spend_usd} of $${data.spend.month_cap_usd}`} href="/agent-activity" />
            <KpiCard label="Time saved (estimate)" value={hours(data.time_saved.minutes)} href="/agent-activity" />
          </section>
          <p className="max-w-prose text-ui-sm text-fg-muted">{data.time_saved.assumption}</p>
          <p className="text-ui-sm text-fg-muted">
            {formatNumber(data.approval.approved)} approved and {formatNumber(data.approval.rejected)} rejected in this period; {data.spend.percent_used}% of this
            month&apos;s allowance is used.
          </p>
        </>
      ) : null}
    </div>
  );
}
