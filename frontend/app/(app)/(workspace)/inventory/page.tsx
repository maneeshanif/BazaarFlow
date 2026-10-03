"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Button, buttonClass } from "@/components/app/Button";
import { DataTable, type Column } from "@/components/app/DataTable";
import { PageHeader } from "@/components/app/PageHeader";
import { Checkbox, SelectInput, TextInput } from "@/components/form/Controls";
import { useLoad } from "@/hooks/useLoad";
import { apiGet } from "@/lib/api/client";
import type { Page, Product } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatNumber } from "@/lib/format";

const PAGE_SIZE = 25;

const SORTS: { value: string; label: string }[] = [
  { value: "name", label: "Name, A to Z" },
  { value: "-created_at", label: "Newest first" },
  { value: "qty", label: "Least stock first" },
  { value: "-price", label: "Price, high to low" },
];

type Row = Product & { status: string; actions: string };

function statusOf(p: Product): string {
  if (!p.active) return "inactive";
  if (p.qty_on_hand === 0) return "out of stock";
  return p.low_stock ? "low stock" : "in stock";
}

/** Products and stock (PRD F-010): search, filter, sort and page through the catalogue; managers add and edit. */
export default function ProductsPage() {
  const { role } = useAuth();
  const canManage = role === "owner" || role === "manager";
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [lowOnly, setLowOnly] = useState(false);
  const [sort, setSort] = useState("name");
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const cursor = cursors[cursors.length - 1] ?? null;

  // wait for a pause in typing before asking the API, and start from the first page again
  useEffect(() => {
    const next = search.trim();
    if (next === q) return; // nothing typed since the last search: leave the current page alone
    const id = setTimeout(() => {
      setQ(next);
      setCursors([null]);
    }, 300);
    return () => clearTimeout(id);
  }, [search, q]);

  const list = useLoad(
    () => apiGet<Page<Product>>("/inventory/", { q, low_stock: lowOnly || undefined, sort, limit: PAGE_SIZE, cursor }),
    [q, lowOnly, sort, cursor],
    (page) => page.items.length === 0,
  );

  const filtered = q !== "" || lowOnly;
  const rows: Row[] = useMemo(
    () => (list.data?.items ?? []).map((p) => ({ ...p, status: statusOf(p), actions: p.id })),
    [list.data],
  );

  const columns: Column<Row>[] = [
    { key: "sku", header: "SKU", mono: true },
    {
      key: "name",
      header: "Name",
      render: (r) => (
        <Link href={`/inventory/${r.id}`} className="font-medium text-action hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-focus">
          {r.name}
        </Link>
      ),
    },
    { key: "category", header: "Category" },
    { key: "qty_on_hand", header: "In stock", numeric: true },
    { key: "reorder_level", header: "Reorder at", numeric: true },
    { key: "price", header: "Price", money: true },
    ...(canManage ? ([{ key: "cost", header: "Cost", money: true }] as Column<Row>[]) : []),
    { key: "status", header: "Status", status: true },
  ];

  const total = list.data?.total ?? 0;
  const from = rows.length === 0 ? 0 : (cursors.length - 1) * PAGE_SIZE + 1;
  const to = (cursors.length - 1) * PAGE_SIZE + rows.length;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Products"
        description="What you sell, what is on the shelf, and what to reorder."
        actions={
          canManage ? (
            <Link href="/inventory/new" className={buttonClass("primary")}>
              Add product
            </Link>
          ) : undefined
        }
      />

      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-surface p-3" role="search" aria-label="Filter products">
        <div className="flex min-w-48 flex-1 flex-col gap-1">
          <label htmlFor="product-search" className="text-ui-xs font-medium text-fg-muted">
            Search
          </label>
          <TextInput id="product-search" type="search" placeholder="Name or SKU" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="product-sort" className="text-ui-xs font-medium text-fg-muted">
            Sort by
          </label>
          <SelectInput
            id="product-sort"
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
        <label className="flex h-control-md items-center gap-2 text-ui-base text-fg">
          <Checkbox
            checked={lowOnly}
            onChange={(e) => {
              setLowOnly(e.target.checked);
              setCursors([null]);
            }}
          />
          Low stock only
        </label>
      </div>

      <DataTable
        caption="Products"
        columns={columns}
        rows={rows}
        state={list.state}
        rowKey={(r) => r.id}
        emptyMessage={filtered ? "No products match these filters." : "You have not added any products yet."}
        emptyAction={
          filtered
            ? {
                label: "Clear filters",
                onClick: () => {
                  setSearch("");
                  setQ("");
                  setLowOnly(false);
                  setCursors([null]);
                },
              }
            : undefined
        }
        errorMessage={list.error?.message ?? "Could not load products."}
        onRetry={list.reload}
      />
      {list.state === "empty" && !filtered && canManage ? (
        <p className="text-ui-sm text-fg-muted">
          Start with your best sellers.{" "}
          <Link href="/inventory/new" className="font-medium text-action hover:underline">
            Add your first product
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
            <Button
              size="sm"
              disabled={!list.data?.next_cursor}
              onClick={() => list.data?.next_cursor && setCursors((c) => [...c, list.data?.next_cursor ?? null])}
            >
              Next
            </Button>
          </span>
        </nav>
      ) : null}
    </div>
  );
}
