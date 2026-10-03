"use client";

import Link from "next/link";
import { useState } from "react";
import { ErrorState } from "@/components/app/StateViews";
import { KpiCard } from "@/components/app/KpiCard";
import { PageHeader } from "@/components/app/PageHeader";
import { SalesTrend } from "@/components/dashboard/SalesTrend";
import { SelectInput } from "@/components/form/Controls";
import { Skeleton } from "@/components/ui/skeleton";
import { useLoad } from "@/hooks/useLoad";
import { apiGet } from "@/lib/api/client";
import type { Dashboard, DashboardRange } from "@/lib/api/types";
import { formatMoney, formatNumber } from "@/lib/format";

const RANGES: { value: DashboardRange; label: string }[] = [
  { value: "today", label: "Today" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
];

const WHEN: Record<DashboardRange, string> = { today: "Today", "7d": "Last 7 days", "30d": "Last 30 days" };

const delta = (percent: number | null): string | undefined => (percent === null ? undefined : `${percent >= 0 ? "+" : "-"}${Math.abs(percent)}%`);

/**
 * The home screen (PRD F-004 for everyone, D-001 for owners and managers). One request returns the figures for the
 * signed-in role; staff never receive profit, udhaar, approvals or the briefing, so there is nothing to hide here.
 */
export function DashboardView() {
  const [range, setRange] = useState<DashboardRange>("today");
  const loaded = useLoad(() => apiGet<Dashboard>("/dashboard/summary", { range }), [range]);
  const data = loaded.data;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Home" description="How the shop is doing." />
      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-surface p-3" role="search" aria-label="Choose the period">
        <div className="flex flex-col gap-1">
          <label htmlFor="range" className="text-ui-xs font-medium text-fg-muted">
            Period
          </label>
          <SelectInput id="range" value={range} onChange={(e) => setRange(e.target.value as DashboardRange)}>
            {RANGES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </SelectInput>
        </div>
      </div>

      {loaded.state === "loading" && !data ? (
        <div role="status" aria-busy="true" aria-label="Loading the dashboard" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : null}
      {loaded.state === "error" ? <ErrorState message={loaded.error?.message ?? "Could not load the dashboard."} onRetry={loaded.reload} /> : null}

      {data ? (
        <>
          {data.briefing ? (
            <section aria-label="Briefing" className="rounded-lg border border-border bg-surface p-4">
              <h2 className="text-ui-md font-semibold text-fg">Briefing</h2>
              <p className="mt-1 max-w-prose text-ui-base text-fg">{data.briefing}</p>
            </section>
          ) : null}

          <section aria-label="Key figures" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <KpiCard label={`${WHEN[data.range]} sales`} value={formatMoney(data.sales.value)} delta={delta(data.sales.change_percent)} href="/orders" />
            {data.profit ? (
              <KpiCard label={`${WHEN[data.range]} profit`} value={formatMoney(data.profit.value)} delta={delta(data.profit.change_percent)} href="/orders" />
            ) : null}
            <KpiCard label={`${WHEN[data.range]} orders`} value={formatNumber(data.orders.value)} delta={delta(data.orders.change_percent)} href="/orders" />
            <KpiCard label="Low-stock items" value={formatNumber(data.low_stock)} href="/inventory" />
            {data.unpaid_udhaar !== null ? <KpiCard label="Unpaid udhaar" value={formatMoney(data.unpaid_udhaar)} href="/customers" /> : null}
            {data.approvals_waiting !== null ? <KpiCard label="Approvals waiting" value={formatNumber(data.approvals_waiting)} href="/approvals" /> : null}
          </section>

          {data.profit && data.profit.orders_without_cost > 0 ? (
            <p className="text-ui-xs text-fg-muted">
              Profit leaves out {data.profit.orders_without_cost} {data.profit.orders_without_cost === 1 ? "order" : "orders"} with a product that has no cost.{" "}
              <Link href="/inventory" className="font-medium text-action hover:underline">
                Add the costs in Products
              </Link>
            </p>
          ) : null}

          <SalesTrend trend={data.trend} />
        </>
      ) : null}
    </div>
  );
}
