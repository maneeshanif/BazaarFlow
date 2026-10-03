"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Button, buttonClass } from "@/components/app/Button";
import { DataTable, type Column } from "@/components/app/DataTable";
import { PageHeader } from "@/components/app/PageHeader";
import { RequireRole } from "@/components/app/RequireRole";
import { Checkbox, SelectInput, TextInput } from "@/components/form/Controls";
import { useLoad } from "@/hooks/useLoad";
import { apiGet } from "@/lib/api/client";
import type { Customer, Page } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";

const PAGE_SIZE = 25;

const SORTS = [
  { value: "name", label: "Name, A to Z" },
  { value: "-balance", label: "Owes the most" },
  { value: "-created_at", label: "Newest first" },
];

type Row = Customer & { status: string };

/** Customers and what they owe (PRD F-009). Owners and managers only. */
function CustomersList() {
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [owingOnly, setOwingOnly] = useState(false);
  const [sort, setSort] = useState("name");
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
    () => apiGet<Page<Customer>>("/customers/", { q, owing_only: owingOnly || undefined, sort, limit: PAGE_SIZE, cursor }),
    [q, owingOnly, sort, cursor],
    (page) => page.items.length === 0,
  );

  const filtered = q !== "" || owingOnly;
  const rows: Row[] = useMemo(
    () => (list.data?.items ?? []).map((c) => ({ ...c, status: Number(c.balance ?? 0) > 0 ? "owes" : "settled" })),
    [list.data],
  );

  const columns: Column<Row>[] = [
    {
      key: "name",
      header: "Name",
      render: (r) => (
        <Link href={`/customers/${r.id}`} className="font-medium text-action hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-focus">
          {r.name ?? r.phone}
        </Link>
      ),
    },
    { key: "phone", header: "Phone", mono: true },
    { key: "address", header: "Address" },
    { key: "balance", header: "They owe", money: true },
    { key: "status", header: "Udhaar", status: true },
  ];

  const total = list.data?.total ?? 0;
  const from = rows.length === 0 ? 0 : (cursors.length - 1) * PAGE_SIZE + 1;
  const to = (cursors.length - 1) * PAGE_SIZE + rows.length;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Customers"
        description="Who buys from you, and who owes you."
        actions={
          <Link href="/customers/new" className={buttonClass("primary")}>
            Add customer
          </Link>
        }
      />

      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-surface p-3" role="search" aria-label="Filter customers">
        <div className="flex min-w-48 flex-1 flex-col gap-1">
          <label htmlFor="customer-search" className="text-ui-xs font-medium text-fg-muted">
            Search
          </label>
          <TextInput id="customer-search" type="search" placeholder="Name or phone" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="customer-sort" className="text-ui-xs font-medium text-fg-muted">
            Sort by
          </label>
          <SelectInput
            id="customer-sort"
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
            checked={owingOnly}
            onChange={(e) => {
              setOwingOnly(e.target.checked);
              setCursors([null]);
            }}
          />
          Owing only
        </label>
      </div>

      <DataTable
        caption="Customers"
        columns={columns}
        rows={rows}
        state={list.state}
        rowKey={(r) => r.id}
        emptyMessage={filtered ? "No customers match these filters." : "You have not added any customers yet."}
        emptyAction={
          filtered
            ? {
                label: "Clear filters",
                onClick: () => {
                  setSearch("");
                  setQ("");
                  setOwingOnly(false);
                  setCursors([null]);
                },
              }
            : undefined
        }
        errorMessage={list.error?.message ?? "Could not load customers."}
        onRetry={list.reload}
      />
      {list.state === "empty" && !filtered ? (
        <p className="text-ui-sm text-fg-muted">
          Customers appear here when you add them or sell to them.{" "}
          <Link href="/customers/new" className="font-medium text-action hover:underline">
            Add your first customer
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

export default function CustomersPage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <CustomersList />
    </RequireRole>
  );
}
