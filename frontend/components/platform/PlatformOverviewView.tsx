"use client";

import Link from "next/link";
import { buttonClass } from "@/components/app/Button";
import { KpiCard } from "@/components/app/KpiCard";
import { PageHeader } from "@/components/app/PageHeader";
import { ErrorState } from "@/components/app/StateViews";
import { Skeleton } from "@/components/ui/skeleton";
import { useLoad } from "@/hooks/useLoad";
import { apiGet } from "@/lib/api/client";
import type { PlatformOverview } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";

const delta = (percent: number | null): string | undefined => (percent === null ? undefined : `${percent >= 0 ? "+" : "-"}${Math.abs(percent)}%`);

/** The platform overview (PRD D-004) for BazaarFlow operators. */
export function PlatformOverviewView() {
  const loaded = useLoad(() => apiGet<PlatformOverview>("/platform/overview"), []);
  const data = loaded.data;
  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Platform overview" description="How BazaarFlow is doing across every shop." />
      {loaded.state === "loading" && !data ? (
        <div role="status" aria-busy="true" aria-label="Loading the overview" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : null}
      {loaded.state === "error" ? <ErrorState message={loaded.error?.message ?? "Could not load the overview."} onRetry={loaded.reload} /> : null}
      {loaded.state === "unauthorized" ? <ErrorState message="Only BazaarFlow operators can open this page." /> : null}

      {data && data.is_empty ? (
        <section aria-label="Nothing to show yet" className="flex flex-col items-start gap-3 rounded-lg border border-border bg-surface p-4">
          <h2 className="text-ui-md font-semibold text-fg">No shops yet</h2>
          <p className="text-ui-sm text-fg-muted">Shops appear here as soon as someone signs up.</p>
        </section>
      ) : null}

      {data && !data.is_empty ? (
        <>
          <section aria-label="Key figures" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <KpiCard label="Shops" value={formatNumber(data.tenants.value)} delta={delta(data.tenants.change_percent)} href="/platform/tenants" />
            <KpiCard label="Active shops (7 days)" value={formatNumber(data.active_tenants_7d)} href="/platform/tenants" />
            <KpiCard label="Messages per day" value={formatNumber(data.messages_per_day_7d)} href="/platform/tenants" />
            <KpiCard label="AI spend this month" value={`$${data.ai_spend_month_usd}`} href="/platform/tenants" />
            <KpiCard label="Agent error rate" value={data.error_rate_percent === null ? "No runs yet" : `${data.error_rate_percent}%`} href="/platform/tenants" />
          </section>
          <p className="max-w-prose text-ui-sm text-fg-muted">
            {formatNumber(data.messages_today)} messages today. {formatNumber(data.agent_runs_7d)} agent runs in the last 7 days; the error rate is the share that failed.{" "}
            {formatNumber(data.demo_tenants)} visitor demo {data.demo_tenants === 1 ? "shop is" : "shops are"} not counted above.
          </p>
          <Link href="/platform/tenants" className={buttonClass("secondary")}>
            Open the shop list
          </Link>
        </>
      ) : null}
    </div>
  );
}
