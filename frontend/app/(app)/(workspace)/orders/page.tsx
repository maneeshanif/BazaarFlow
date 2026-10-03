"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Button, buttonClass } from "@/components/app/Button";
import { DataTable, type Column } from "@/components/app/DataTable";
import { PageHeader } from "@/components/app/PageHeader";
import { SelectInput, TextInput } from "@/components/form/Controls";
import { useLoad } from "@/hooks/useLoad";
import { apiGet } from "@/lib/api/client";
import type { OrderSummary, Page } from "@/lib/api/types";
import { formatDateTime, formatNumber } from "@/lib/format";

const PAGE_SIZE = 25;

const STATUSES = [
  { value: "", label: "Any status" },
  { value: "posted", label: "Posted" },
  { value: "reversed", label: "Reversed" },
  { value: "draft", label: "Draft" },
];

const SORTS = [
  { value: "-created_at", label: "Newest first" },
  { value: "created_at", label: "Oldest first" },
  { value: "-total", label: "Biggest first" },
];

type Row = OrderSummary & { when: string; ref: string; who: string };

/** Orders (PRD F-008): every sale, newest first, with what is still owed on it. */
export default function OrdersPage() {
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState("-created_at");
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const cursor = cursors[cursors.length - 1] ?? null;

  useEffect(() => {
    const next = search.trim();
    if (next === q) return;
    const id = setTimeout(() => {
      setQ(next);
      setCursors([null]);
    }, 300);
    return () => clearTimeout(id);
  }, [search, q]);

  const list = useLoad(
    () => apiGet<Page<OrderSummary>>("/orders/", { q, status, sort, limit: PAGE_SIZE, cursor }),
    [q, status, sort, cursor],
    (page) => page.items.length === 0,
  );

  const filtered = q !== "" || status !== "";
  const rows: Row[] = useMemo(
    () =>
      (list.data?.items ?? []).map((o) => ({
        ...o,
        when: formatDateTime(o.created_at),
        ref: o.id.slice(0, 8).toUpperCase(),
        who: o.customer_name ?? "Walk-in",
      })),
    [list.data],
  );

  const columns: Column<Row>[] = [
    {
      key: "ref",
      header: "Order",
      mono: true,
      render: (r) => (
        <Link href={`/orders/${r.id}`} className="font-medium text-action hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-focus">
          {r.ref}
        </Link>
      ),
    },
    { key: "when", header: "When" },
    { key: "who", header: "Customer" },
    { key: "item_count", header: "Items", numeric: true },
    { key: "total", header: "Total", money: true },
    { key: "amount_due", header: "Still owed", money: true },
    { key: "status", header: "Status", status: true },
  ];

  const total = list.data?.total ?? 0;
  const from = rows.length === 0 ? 0 : (cursors.length - 1) * PAGE_SIZE + 1;
  const to = (cursors.length - 1) * PAGE_SIZE + rows.length;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Orders"
        description="Every sale you have posted."
        actions={
          <Link href="/sales/new" className={buttonClass("primary")}>
            New sale
          </Link>
        }
      />

      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-surface p-3" role="search" aria-label="Filter orders">
        <div className="flex min-w-48 flex-1 flex-col gap-1">
          <label htmlFor="order-search" className="text-ui-xs font-medium text-fg-muted">
            Search
          </label>
          <TextInput id="order-search" type="search" placeholder="Customer or product" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="order-status" className="text-ui-xs font-medium text-fg-muted">
            Status
          </label>
          <SelectInput
            id="order-status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setCursors([null]);
            }}
          >
            {STATUSES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </SelectInput>
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="order-sort" className="text-ui-xs font-medium text-fg-muted">
            Sort by
          </label>
          <SelectInput
            id="order-sort"
            value={sort}
            onChange={(e) => {
              setSort(e.target.value);
              setCursors([null]);
            }}
          >
            {SORTS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </SelectInput>
        </div>
      </div>

      <DataTable
        caption="Orders"
        columns={columns}
        rows={rows}
        state={list.state}
        rowKey={(r) => r.id}
        emptyMessage={filtered ? "No orders match these filters." : "No sales yet."}
        emptyAction={
          filtered
            ? {
                label: "Clear filters",
                onClick: () => {
                  setSearch("");
                  setQ("");
                  setStatus("");
                  setCursors([null]);
                },
              }
            : undefined
        }
        errorMessage={list.error?.message ?? "Could not load orders."}
        onRetry={list.reload}
      />
      {list.state === "empty" && !filtered ? (
        <p className="text-ui-sm text-fg-muted">
          Sales appear here once you post them.{" "}
          <Link href="/sales/new" className="font-medium text-action hover:underline">
            Record your first sale
          </Link>
          .
        </p>
      ) : null}

      {list.state === "ready" ? (
        <nav aria-label="Pagination" className="flex items-center justify-between gap-2 text-ui-sm text-fg-muted">
          <span>
            Showing {formatNumber(from)} to {formatNumber(to)} of {formatNumber(total)}
          </span>
          <span className="flex gap-2">
            <Button size="sm" disabled={cursors.length === 1} onClick={() => setCursors((c) => c.slice(0, -1))}>
              Previous
            </Button>
            <Button size="sm" disabled={!list.data?.next_cursor} onClick={() => list.data?.next_cursor && setCursors((c) => [...c, list.data?.next_cursor ?? null])}>
              Next
            </Button>
          </span>
        </nav>
      ) : null}
    </div>
  );
}
