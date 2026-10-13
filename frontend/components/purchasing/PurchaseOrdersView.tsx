"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/app/Button";
import { DataTable, type Column } from "@/components/app/DataTable";
import { PageHeader } from "@/components/app/PageHeader";
import { SelectInput } from "@/components/form/Controls";
import { useLoad } from "@/hooks/useLoad";
import { useSubmit } from "@/hooks/useSubmit";
import { apiGet, apiPost } from "@/lib/api/client";
import type { Page, PurchaseOrder, PurchaseOrderDetail } from "@/lib/api/types";
import { formatDateTime, formatNumber } from "@/lib/format";

const PAGE_SIZE = 25;
const STATUSES = [
  { value: "", label: "Every order" },
  { value: "drafted", label: "Drafts" },
  { value: "sent", label: "Sent" },
  { value: "cancelled", label: "Cancelled" },
];

type Row = PurchaseOrder & { when: string; note: string; actions: string };

/**
 * Draft purchase orders (PRD W-006): what the low-stock automation worked out you should reorder, per vendor. An order
 * becomes "sent" when its WhatsApp message is approved and goes out; a draft can be cancelled. Nothing here changes
 * stock or what you owe: receiving goods and paying the vendor stay in Vendors.
 */
export function PurchaseOrdersView() {
  const [status, setStatus] = useState("");
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const cursor = cursors[cursors.length - 1] ?? null;
  const list = useLoad(
    () => apiGet<Page<PurchaseOrder>>("/purchase-orders/", { status: status || undefined, limit: PAGE_SIZE, cursor }),
    [status, cursor],
    (page) => page.items.length === 0,
  );
  const cancel = useSubmit((id: string) => apiPost<PurchaseOrderDetail>(`/purchase-orders/${id}/cancel`));

  const inFlight = useRef(new Set<string>()); // a second click while the first is still running does nothing

  async function cancelDraft(id: string) {
    if (inFlight.current.has(id)) return;
    inFlight.current.add(id);
    try {
      const done = await cancel.run(id);
      if (done) toast.success("Draft cancelled");
      else if (cancel.error) toast.error(cancel.error.message);
      list.reload();
    } finally {
      inFlight.current.delete(id);
    }
  }

  const rows: Row[] = (list.data?.items ?? []).map((o) => ({
    ...o,
    when: formatDateTime(o.sent_at ?? o.created_at),
    note: o.status === "drafted" && !o.vendor_has_phone ? "No phone number for this vendor, so no message was drafted. Add one in Vendors." : "",
    actions: o.status,
  }));

  const columns: Column<Row>[] = [
    { key: "vendor_name", header: "Vendor" },
    { key: "item_count", header: "Items", numeric: true },
    { key: "total", header: "Estimated total", money: true },
    { key: "status", header: "Status", status: true },
    { key: "when", header: "When" },
    { key: "note", header: "Note" },
    {
      key: "actions",
      header: "",
      render: (r) =>
        r.status === "drafted" ? (
          <Button size="sm" variant="danger" onClick={() => void cancelDraft(r.id)}>
            Cancel
          </Button>
        ) : null,
    },
  ];

  const total = list.data?.total ?? 0;
  const from = rows.length === 0 ? 0 : (cursors.length - 1) * PAGE_SIZE + 1;
  const to = (cursors.length - 1) * PAGE_SIZE + rows.length;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Purchase orders" description="What to reorder from each vendor when stock runs low." />
      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-surface p-3" role="search" aria-label="Filter orders">
        <div className="flex flex-col gap-1">
          <label htmlFor="po-status" className="text-ui-xs font-medium text-fg-muted">
            Show
          </label>
          <SelectInput
            id="po-status"
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
      </div>
      <DataTable
        caption="Purchase orders"
        columns={columns}
        rows={rows}
        state={list.state}
        rowKey={(r) => r.id}
        emptyMessage={status ? "No orders with this status." : "No purchase orders yet. Switch on the low-stock automation and they appear here."}
        emptyAction={status ? { label: "Clear filter", onClick: () => setStatus("") } : undefined}
        errorMessage={list.error?.message ?? "Could not load purchase orders."}
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
