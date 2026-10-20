"use client";

import Link from "next/link";
import { useState } from "react";
import { buttonClass } from "@/components/app/Button";
import { DataTable, type Column } from "@/components/app/DataTable";
import { KpiCard } from "@/components/app/KpiCard";
import { PageHeader } from "@/components/app/PageHeader";
import { ErrorState } from "@/components/app/StateViews";
import { SelectInput } from "@/components/form/Controls";
import { Skeleton } from "@/components/ui/skeleton";
import { useLoad } from "@/hooks/useLoad";
import { apiGet } from "@/lib/api/client";
import type { CashBookEntry, DashboardRange, FinanceOverview, Page } from "@/lib/api/types";
import { formatDateTime, formatMoney, formatNumber } from "@/lib/format";

const RANGES: { value: DashboardRange; label: string }[] = [
  { value: "today", label: "Today" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
];

const delta = (percent: number | null): string | undefined => (percent === null ? undefined : `${percent >= 0 ? "+" : "-"}${Math.abs(percent)}%`);

const WEEKDAY = new Intl.DateTimeFormat("en-GB", { weekday: "short", timeZone: "UTC" });
const SHORT_DAY = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });

/** Revenue per day as bars (PRD §8: bar charts compare). Every figure is from the server and also in a table for screen readers. */
function RevenueTrend({ trend }: { trend: FinanceOverview["trend"] }) {
  const max = Math.max(...trend.map((d) => Number(d.revenue)), 0);
  const label = `Revenue, last ${trend.length} days`;
  if (max === 0) {
    return (
      <section aria-label={label} className="flex flex-col items-start gap-3 rounded-card border-2 border-line-strong bg-surface-raised p-6 shadow-card">
        <h2 className="text-ui-md font-semibold text-fg">{label}</h2>
        <p className="text-ui-sm text-fg-muted">No sales in this period. Record a sale and the days will fill in here.</p>
        <Link href="/sales/new" className={buttonClass("primary")}>
          New sale
        </Link>
      </section>
    );
  }
  const month = trend.length > 7;
  return (
    <section aria-label={label} className="rounded-card border-2 border-line-strong bg-surface-raised p-6 shadow-card">
      <h2 className="text-ui-md font-semibold text-fg">{label}</h2>
      <div className="mt-4 flex h-40 items-end gap-1" aria-hidden="true">
        {trend.map((d) => (
          <div key={d.day} className="flex h-full min-w-0 flex-1 flex-col justify-end gap-1">
            <div className="rounded-sm bg-action" style={{ height: `${Math.max((Number(d.revenue) / max) * 100, d.orders > 0 ? 3 : 0)}%` }} title={`${d.day}: ${formatMoney(d.revenue)}`} />
            {month ? null : <span className="text-center text-ui-xs text-fg-muted">{WEEKDAY.format(new Date(`${d.day}T00:00:00Z`))}</span>}
          </div>
        ))}
      </div>
      <table className="sr-only">
        <caption>{label}</caption>
        <thead>
          <tr>
            <th scope="col">Day</th>
            <th scope="col">Revenue</th>
            <th scope="col">Orders</th>
          </tr>
        </thead>
        <tbody>
          {trend.map((d) => (
            <tr key={d.day}>
              <th scope="row">{SHORT_DAY.format(new Date(`${d.day}T00:00:00Z`))}</th>
              <td>{formatMoney(d.revenue)}</td>
              <td>{d.orders}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

type AgingRow = { label: string; amount: string; customers: number };

const agingColumns: Column<AgingRow>[] = [
  { key: "label", header: "Waiting for" },
  { key: "customers", header: "Customers", numeric: true },
  { key: "amount", header: "They owe", money: true },
];

const KIND: Record<CashBookEntry["kind"], string> = {
  sale_payment: "Sale paid",
  udhaar_payment: "Udhaar payment",
  vendor_payment: "Paid to a vendor",
};

type LedgerRow = CashBookEntry & { when: string; what: string; signed: string };

const ledgerColumns: Column<LedgerRow>[] = [
  { key: "when", header: "When" },
  { key: "what", header: "What happened" },
  { key: "method", header: "Paid by" },
  { key: "signed", header: "Amount", money: true },
];

function CashBook() {
  const [direction, setDirection] = useState("");
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const cursor = cursors[cursors.length - 1] ?? null;
  const list = useLoad(
    () => apiGet<Page<CashBookEntry>>("/finance/ledger", { direction: direction || undefined, limit: 25, cursor }),
    [direction, cursor],
    (page) => page.items.length === 0,
  );
  const rows: LedgerRow[] = (list.data?.items ?? []).map((e) => ({
    ...e,
    when: formatDateTime(e.created_at),
    what: KIND[e.kind],
    signed: e.direction === "out" ? `-${e.amount}` : e.amount,
  }));
  return (
    <section aria-label="Cash book" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-ui-md font-semibold text-fg">Cash book</h2>
          <p className="text-ui-sm text-fg-muted">Money you received and money you paid out, newest first.</p>
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="cash-direction" className="text-ui-xs font-medium text-fg-muted">
            Show
          </label>
          <SelectInput
            id="cash-direction"
            value={direction}
            onChange={(e) => {
              setDirection(e.target.value);
              setCursors([null]);
            }}
          >
            <option value="">Everything</option>
            <option value="in">Money in</option>
            <option value="out">Money out</option>
          </SelectInput>
        </div>
      </div>
      <DataTable
        caption="Cash book"
        columns={ledgerColumns}
        rows={rows}
        state={list.state}
        rowKey={(r) => r.id}
        emptyMessage="No money has moved yet."
        errorMessage={list.error?.message ?? "Could not load the cash book."}
        onRetry={list.reload}
      />
      {list.state === "ready" ? (
        <nav aria-label="Cash book pages" className="flex justify-end gap-2 text-ui-sm">
          <button type="button" className={buttonClass("secondary")} disabled={cursors.length === 1} onClick={() => setCursors((c) => c.slice(0, -1))}>
            Previous
          </button>
          <button
            type="button"
            className={buttonClass("secondary")}
            disabled={!list.data?.next_cursor}
            onClick={() => list.data?.next_cursor && setCursors((c) => [...c, list.data?.next_cursor ?? null])}
          >
            Next
          </button>
        </nav>
      ) : null}
    </section>
  );
}

type Props = {
  endpoint: "/finance/overview" | "/finance/dashboard";
  title: string;
  description: string;
  /** F-013 shows the cash book under the figures; the D-002 dashboard is the figures alone */
  showCashBook?: boolean;
};

/**
 * Finance figures (PRD F-013 for owners and managers, D-002 for owners). One request returns the figures for the
 * signed-in role: a manager never receives margin or vendor payables, so there is nothing to hide here.
 */
export function FinanceView({ endpoint, title, description, showCashBook = false }: Props) {
  const [range, setRange] = useState<DashboardRange>("30d");
  const loaded = useLoad(() => apiGet<FinanceOverview>(endpoint, { range }), [endpoint, range]);
  const data = loaded.data;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={title} description={description} />
      <div className="flex flex-wrap items-end gap-3 rounded-card border-2 border-line-strong bg-surface-raised p-5 shadow-card" role="search" aria-label="Choose the period">
        <div className="flex flex-col gap-1">
          <label htmlFor="finance-range" className="text-ui-xs font-medium text-fg-muted">
            Period
          </label>
          <SelectInput id="finance-range" value={range} onChange={(e) => setRange(e.target.value as DashboardRange)}>
            {RANGES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </SelectInput>
        </div>
      </div>

      {loaded.state === "loading" && !data ? (
        <div role="status" aria-busy="true" aria-label="Loading finance figures" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : null}
      {loaded.state === "error" ? <ErrorState message={loaded.error?.message ?? "Could not load the finance figures."} onRetry={loaded.reload} /> : null}
      {loaded.state === "unauthorized" ? <ErrorState message="Only the shop owner can open this page." /> : null}

      {data && data.is_empty ? (
        <section aria-label="Nothing to show yet" className="flex flex-col items-start gap-3 rounded-card border-2 border-line-strong bg-surface-raised p-6 shadow-card">
          <h2 className="text-ui-md font-semibold text-fg">Nothing to show yet</h2>
          <p className="max-w-prose text-ui-sm text-fg-muted">Your revenue, receivables and payables appear here once you record a sale or a vendor bill.</p>
          <Link href="/sales/new" className={buttonClass("primary")}>
            New sale
          </Link>
        </section>
      ) : null}

      {data && !data.is_empty ? (
        <>
          <section aria-label="Key figures" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <KpiCard label="Revenue" value={formatMoney(data.revenue.value)} delta={delta(data.revenue.change_percent)} href="/orders" />
            {data.gross_margin ? (
              <KpiCard label="Gross margin" value={data.gross_margin.margin_percent === null ? "Not known" : `${data.gross_margin.margin_percent}%`} href="/orders" />
            ) : null}
            <KpiCard label="Owed by customers" value={formatMoney(data.receivables.total)} href="/customers" />
            {data.payables ? <KpiCard label="Owed to vendors" value={formatMoney(data.payables.total)} href="/vendors" /> : null}
            <KpiCard label="Sold on credit" value={data.split.credit_percent === null ? "None" : `${data.split.credit_percent}%`} href="/orders" />
          </section>

          {data.gross_margin && data.gross_margin.orders_without_cost > 0 ? (
            <p className="text-ui-sm text-fg-muted">
              The margin leaves out {formatNumber(data.gross_margin.orders_without_cost)} {data.gross_margin.orders_without_cost === 1 ? "order" : "orders"} because a product has no cost price.
            </p>
          ) : null}

          <RevenueTrend trend={data.trend} />

          <section aria-label="Cash and credit" className="rounded-card border-2 border-line-strong bg-surface-raised p-6 shadow-card">
            <h2 className="text-ui-md font-semibold text-fg">Cash and credit</h2>
            <dl className="mt-2 grid grid-cols-2 gap-4 text-ui-sm">
              <div>
                <dt className="text-fg-muted">Paid at the counter</dt>
                <dd className="font-mono text-ui-lg font-semibold tabular-nums text-fg">{formatMoney(data.split.paid_now)}</dd>
              </div>
              <div>
                <dt className="text-fg-muted">Put on udhaar</dt>
                <dd className="font-mono text-ui-lg font-semibold tabular-nums text-fg">{formatMoney(data.split.on_credit)}</dd>
              </div>
            </dl>
          </section>

          <section aria-label="Receivables" className="flex flex-col gap-3">
            <h2 className="text-ui-md font-semibold text-fg">Who owes you, by how long</h2>
            <DataTable caption="Receivables aging" columns={agingColumns} rows={data.receivables.buckets} state="ready" rowKey={(r) => r.label} />
          </section>

          {data.payables && data.payables.total !== "0.00" ? (
            <p className="text-ui-sm text-fg-muted">
              You owe {formatMoney(data.payables.total)} to {formatNumber(data.payables.vendors)} {data.payables.vendors === 1 ? "vendor" : "vendors"}; {formatMoney(data.payables.overdue)} is overdue.{" "}
              <Link href="/vendors" className="font-medium text-action hover:underline">
                Open vendors
              </Link>
              .
            </p>
          ) : null}
        </>
      ) : null}

      {showCashBook ? <CashBook /> : null}
    </div>
  );
}
