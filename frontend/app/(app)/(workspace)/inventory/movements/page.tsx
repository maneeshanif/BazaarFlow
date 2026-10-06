"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/app/Button";
import { DataTable, type Column } from "@/components/app/DataTable";
import { PageHeader } from "@/components/app/PageHeader";
import { RequireRole } from "@/components/app/RequireRole";
import { SelectInput } from "@/components/form/Controls";
import { useLoad } from "@/hooks/useLoad";
import { apiGet } from "@/lib/api/client";
import type { Page, StockMovementListItem } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";

const PAGE_SIZE = 25;

const REASONS = [
  { value: "", label: "Every reason" },
  { value: "opening", label: "Opening stock" },
  { value: "sale", label: "Sale" },
  { value: "purchase", label: "Purchase" },
  { value: "adjustment", label: "Adjustment" },
  { value: "return", label: "Return" },
  { value: "reversal", label: "Reversal" },
];

type Row = StockMovementListItem & { change: string; when: string };

/** Every stock movement of the shop (PRD F-011). Owners and managers only. */
function MovementsList() {
  const [reason, setReason] = useState("");
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const cursor = cursors[cursors.length - 1] ?? null;

  const list = useLoad(
    () => apiGet<Page<StockMovementListItem>>("/inventory/movements", { reason: reason || undefined, limit: PAGE_SIZE, cursor }),
    [reason, cursor],
    (page) => page.items.length === 0,
  );

  const rows: Row[] = (list.data?.items ?? []).map((m) => ({
    ...m,
    change: m.delta > 0 ? `+${m.delta}` : String(m.delta),
    when: new Date(m.created_at).toLocaleString("en-PK", { dateStyle: "medium", timeStyle: "short" }),
  }));

  const columns: Column<Row>[] = [
    { key: "when", header: "When" },
    {
      key: "product_name",
      header: "Product",
      render: (r) => (
        <Link href={`/inventory/${r.product_id}`} className="font-medium text-action hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-focus">
          {r.product_name}
        </Link>
      ),
    },
    { key: "sku", header: "SKU", mono: true },
    { key: "change", header: "Change", numeric: true },
    { key: "reason", header: "Reason" },
    { key: "actor_type", header: "By" },
    { key: "note", header: "Note" },
  ];

  const total = list.data?.total ?? 0;
  const from = rows.length === 0 ? 0 : (cursors.length - 1) * PAGE_SIZE + 1;
  const to = (cursors.length - 1) * PAGE_SIZE + rows.length;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Stock movements" description="Every change to your stock, and why it happened." />

      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-surface p-3" role="search" aria-label="Filter stock movements">
        <div className="flex flex-col gap-1">
          <label htmlFor="movement-reason" className="text-ui-xs font-medium text-fg-muted">
            Reason
          </label>
          <SelectInput
            id="movement-reason"
            value={reason}
            onChange={(e) => {
              setReason(e.target.value);
              setCursors([null]);
            }}
          >
            {REASONS.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </SelectInput>
        </div>
      </div>

      <DataTable
        caption="Stock movements"
        columns={columns}
        rows={rows}
        state={list.state}
        rowKey={(r) => r.id}
        emptyMessage={reason ? "No movements match this reason." : "No stock has moved yet."}
        emptyAction={reason ? { label: "Clear filter", onClick: () => { setReason(""); setCursors([null]); } } : undefined}
        errorMessage={list.error?.message ?? "Could not load stock movements."}
        onRetry={list.reload}
      />

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

export default function MovementsPage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <MovementsList />
    </RequireRole>
  );
}
