"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Button, buttonClass } from "@/components/app/Button";
import { DataTable, type Column } from "@/components/app/DataTable";
import { PageHeader } from "@/components/app/PageHeader";
import { RequireRole } from "@/components/app/RequireRole";
import { Checkbox, TextInput } from "@/components/form/Controls";
import { useLoad } from "@/hooks/useLoad";
import { apiGet } from "@/lib/api/client";
import type { Page, ShopVendor } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";

const PAGE_SIZE = 25;

type Row = ShopVendor & { status: string };

/** Vendors and what you owe them (PRD F-012). Owners and managers only. */
function VendorsList() {
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [owingOnly, setOwingOnly] = useState(false);
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
    () => apiGet<Page<ShopVendor>>("/vendors/", { q, owing_only: owingOnly || undefined, limit: PAGE_SIZE, cursor }),
    [q, owingOnly, cursor],
    (page) => page.items.length === 0,
  );

  const filtered = q !== "" || owingOnly;
  const rows: Row[] = useMemo(
    () => (list.data?.items ?? []).map((v) => ({ ...v, status: Number(v.balance) > 0 ? "owes" : "settled" })),
    [list.data],
  );

  const columns: Column<Row>[] = [
    {
      key: "name",
      header: "Name",
      render: (r) => (
        <Link href={`/vendors/${r.id}`} className="font-medium text-action hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-focus">
          {r.name}
        </Link>
      ),
    },
    { key: "phone", header: "Phone", mono: true },
    { key: "balance", header: "You owe", money: true },
    { key: "status", header: "Payables", status: true },
  ];

  const total = list.data?.total ?? 0;
  const from = rows.length === 0 ? 0 : (cursors.length - 1) * PAGE_SIZE + 1;
  const to = (cursors.length - 1) * PAGE_SIZE + rows.length;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Vendors"
        description="Who you buy stock from, and what you owe them."
        actions={
          <Link href="/vendors/new" className={buttonClass("primary")}>
            Add vendor
          </Link>
        }
      />

      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-surface p-3" role="search" aria-label="Filter vendors">
        <div className="flex min-w-48 flex-1 flex-col gap-1">
          <label htmlFor="vendor-search" className="text-ui-xs font-medium text-fg-muted">
            Search
          </label>
          <TextInput id="vendor-search" type="search" placeholder="Name or phone" value={search} onChange={(e) => setSearch(e.target.value)} />
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
        caption="Vendors"
        columns={columns}
        rows={rows}
        state={list.state}
        rowKey={(r) => r.id}
        emptyMessage={filtered ? "No vendors match these filters." : "You have not added any vendors yet."}
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
        errorMessage={list.error?.message ?? "Could not load vendors."}
        onRetry={list.reload}
      />
      {list.state === "empty" && !filtered ? (
        <p className="text-ui-sm text-fg-muted">
          Vendors appear here when you add them.{" "}
          <Link href="/vendors/new" className="font-medium text-action hover:underline">
            Add your first vendor
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

export default function VendorsPage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <VendorsList />
    </RequireRole>
  );
}
