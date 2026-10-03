"use client";

import { DataTable, type Column } from "@/components/app/DataTable";
import { KpiCard } from "@/components/app/KpiCard";
import { PageHeader } from "@/components/app/PageHeader";
import { StatusBadge } from "@/components/app/StatusBadge";
import { FormField } from "@/components/form/FormField";
import { FormShell } from "@/components/form/FormShell";
import { Input } from "@/components/ui/input";
import { formatDateTime, formatMoney } from "@/lib/format";

type Row = {
  sku: string;
  name: string;
  category: string;
  stock: number;
  reorder: number;
  price: string;
  cost: string;
  vendor: string;
  updated: string;
  status: string;
};

const columns: Column<Row>[] = [
  { key: "sku", header: "SKU", mono: true },
  { key: "name", header: "Name" },
  { key: "category", header: "Category" },
  { key: "stock", header: "In stock", numeric: true },
  { key: "reorder", header: "Reorder level", numeric: true },
  { key: "price", header: "Price", money: true },
  { key: "cost", header: "Cost", money: true },
  { key: "vendor", header: "Vendor" },
  { key: "updated", header: "Updated" },
  { key: "status", header: "Status", status: true },
];

const rows: Row[] = [
  { sku: "SHIRT-001", name: "Classic Oxford Shirt", category: "Apparel", stock: 50, reorder: 10, price: "2500", cost: "1800", vendor: "Karim Traders", updated: formatDateTime("2026-10-01T20:30:00Z"), status: "in stock" },
  { sku: "JEANS-002", name: "Slim Fit Denim", category: "Apparel", stock: 4, reorder: 8, price: "3800.5", cost: "2600", vendor: "Noor Garments", updated: formatDateTime("2026-09-28T09:00:00Z"), status: "low stock" },
  { sku: "SHOES-003", name: "Leather Loafers", category: "Footwear", stock: 0, reorder: 5, price: "5500", cost: "3900", vendor: "Karim Traders", updated: formatDateTime("2026-09-20T15:10:00Z"), status: "out of stock" },
];

/** Demonstrates every foundation component. Reachable at /ui-preview only in development or with UI_PREVIEW=1. */
export default function PreviewContent() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Home" description="Foundation components, rendered with sample data." />

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Today's sales" value={formatMoney(42500)} delta="+8%" href="/orders" />
        <KpiCard label="Profit today" value={formatMoney(9800)} delta="+3%" href="/orders" />
        <KpiCard label="Orders today" value="31" delta="-2%" href="/orders" />
        <KpiCard label="Low-stock items" value="6" href="/inventory" />
      </div>

      <section aria-label="Products" className="flex flex-col gap-2">
        <h2 className="text-ui-md font-semibold">Products</h2>
        <DataTable caption="Products" columns={columns} rows={rows} state="ready" />
      </section>

      <FormShell
        title="New sale"
        status="draft"
        filters={
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <FormField id="customer" label="Customer" required hint="Leave empty for a walk-in sale">
              <Input id="customer" placeholder="Search customers" />
            </FormField>
            <FormField id="payment" label="Payment method" required error="Choose how the customer paid.">
              <Input id="payment" aria-invalid />
            </FormField>
          </div>
        }
        totals={<p className="text-right font-mono text-ui-xl tabular-nums">{formatMoney(3000)}</p>}
        actions={
          <>
            <button type="button" className="h-control-md rounded-md border border-border bg-surface px-3 text-ui-base">
              Save draft
            </button>
            <button type="button" className="h-control-md rounded-md bg-action px-3 text-ui-base font-medium text-fg-inverse hover:bg-action-hover">
              Post sale
            </button>
          </>
        }
        audit={<p>Created by Staff - stock will drop by 5 when posted.</p>}
      >
        <DataTable caption="Sale lines" columns={columns.slice(0, 4)} rows={rows} state="ready" />
      </FormShell>

      <section aria-label="States" className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <DataTable caption="Loading" columns={columns.slice(0, 3)} rows={[]} state="loading" />
        <DataTable caption="Empty" columns={columns.slice(0, 3)} rows={[]} state="empty" emptyMessage="No products yet." emptyAction={{ label: "Add product", onClick: () => undefined }} />
        <DataTable caption="Error" columns={columns.slice(0, 3)} rows={[]} state="error" errorMessage="Could not load products." onRetry={() => undefined} />
        <DataTable caption="Unauthorized" columns={columns.slice(0, 3)} rows={[]} state="unauthorized" />
      </section>

      <div className="flex flex-wrap gap-2">
        {["posted", "pending", "scheduled", "failed", "needs_human", "ai_handling", "draft"].map((s) => (
          <StatusBadge key={s} status={s} />
        ))}
      </div>
    </div>
  );
}
