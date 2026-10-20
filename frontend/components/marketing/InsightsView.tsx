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
import type { DashboardRange, MarketingInsights } from "@/lib/api/types";
import { formatDateTime, formatNumber } from "@/lib/format";

const RANGES: { value: DashboardRange; label: string }[] = [
  { value: "today", label: "Today" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
];

const delta = (p: number | null): string | undefined => (p === null ? undefined : `${p >= 0 ? "+" : "-"}${Math.abs(p)}%`);

/** Marketing insights (PRD F-017): how your posts did. Owners and managers. */
export function InsightsView() {
  const [range, setRange] = useState<DashboardRange>("30d");
  const loaded = useLoad(() => apiGet<MarketingInsights>("/marketing/insights", { range }), [range]);
  const data = loaded.data;
  const max = Math.max(...(data?.trend.map((d) => d.published) ?? [0]), 0);

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Marketing insights" description="How your Facebook posts did." />
      <div className="flex flex-wrap items-end gap-3 rounded-card border-2 border-line-strong bg-surface-raised p-5 shadow-card" role="search" aria-label="Choose the period">
        <div className="flex flex-col gap-1">
          <label htmlFor="insight-range" className="text-ui-xs font-medium text-fg-muted">
            Period
          </label>
          <SelectInput id="insight-range" value={range} onChange={(e) => setRange(e.target.value as DashboardRange)}>
            {RANGES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </SelectInput>
        </div>
      </div>
      {loaded.state === "loading" && !data ? <Skeleton className="h-32 w-full" /> : null}
      {loaded.state === "error" ? <ErrorState message={loaded.error?.message ?? "Could not load the insights."} onRetry={loaded.reload} /> : null}

      {data?.is_empty ? (
        <section aria-label="Nothing to show yet" className="flex flex-col items-start gap-3 rounded-card border-2 border-line-strong bg-surface-raised p-6 shadow-card">
          <h2 className="text-ui-md font-semibold text-fg">No posts yet</h2>
          <p className="text-ui-sm text-fg-muted">Publish a post, or switch on the posting schedule, and its results show up here.</p>
          <Link href="/marketing/schedule" className={buttonClass("primary")}>
            Posting schedule
          </Link>
        </section>
      ) : null}

      {data && !data.is_empty ? (
        <>
          <section aria-label="Key figures" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <KpiCard label="Posts published" value={formatNumber(data.published.value)} delta={delta(data.published.change_percent)} href="/marketing/activity" />
            <KpiCard label="Went out as planned" value={data.success_percent === null ? "No posts yet" : `${data.success_percent}%`} href="/marketing/activity" />
            <KpiCard label="Failed" value={formatNumber(data.failed)} href="/marketing/activity" />
            <KpiCard label="Waiting to go out" value={formatNumber(data.queued)} href="/marketing/activity" />
          </section>
          <p className="text-ui-sm text-fg-muted">{formatNumber(data.from_schedule)} of the published posts were written by your schedule.</p>

          <section aria-label="Posts per day" className="rounded-card border-2 border-line-strong bg-surface-raised p-6 shadow-card">
            <h2 className="text-ui-md font-semibold text-fg">Posts per day</h2>
            <div className="mt-4 flex h-32 items-end gap-1" aria-hidden="true">
              {data.trend.map((d) => (
                <div key={d.day} className="flex h-full min-w-0 flex-1 flex-col justify-end">
                  <div className="rounded-sm bg-action" style={{ height: `${max === 0 ? 0 : Math.max((d.published / max) * 100, d.published > 0 ? 4 : 0)}%` }} title={`${d.day}: ${d.published}`} />
                </div>
              ))}
            </div>
            <table className="sr-only">
              <caption>Posts published per day</caption>
              <thead>
                <tr>
                  <th scope="col">Day</th>
                  <th scope="col">Posts</th>
                </tr>
              </thead>
              <tbody>
                {data.trend.map((d) => (
                  <tr key={d.day}>
                    <th scope="row">{d.day}</th>
                    <td>{d.published}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section aria-label="Latest posts" className="flex flex-col gap-2">
            <h2 className="text-ui-md font-semibold text-fg">Latest posts and comments</h2>
            {data.engagement_note ? (
              <p role="status" className="rounded-md border border-warning-border bg-warning-subtle px-3 py-2 text-ui-sm text-warning">
                {data.engagement_note}
              </p>
            ) : null}
            {data.top_posts.length === 0 ? (
              <p className="text-ui-sm text-fg-muted">No published posts yet.</p>
            ) : (
              <ul className="flex flex-col gap-1">
                {data.top_posts.map((p) => (
                  <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 rounded-card border-2 border-line-strong bg-surface-raised shadow-card px-3 py-2 text-ui-sm">
                    <span className="text-fg">{p.title}</span>
                    <span className="text-fg-muted">
                      {formatDateTime(p.published_at)} · {p.comments === null ? "comments not available" : `${formatNumber(p.comments)} ${p.comments === 1 ? "comment" : "comments"}`}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
