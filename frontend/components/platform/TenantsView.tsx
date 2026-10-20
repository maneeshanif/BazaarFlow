"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/app/Button";
import { ConfirmDialog } from "@/components/app/ConfirmDialog";
import { DataTable, type Column } from "@/components/app/DataTable";
import { PageHeader } from "@/components/app/PageHeader";
import { Checkbox, SelectInput, TextInput } from "@/components/form/Controls";
import { useLoad } from "@/hooks/useLoad";
import { useSubmit } from "@/hooks/useSubmit";
import { apiGet, apiPost } from "@/lib/api/client";
import type { Page, PlatformTenant } from "@/lib/api/types";
import { formatDateTime, formatNumber } from "@/lib/format";

const PAGE_SIZE = 25;

type Row = PlatformTenant & { activity: string; kind: string; actions: string };

/** Every shop on the platform (PRD F-025): size, last activity, and suspend or reactivate. Operators only. */
export function TenantsView() {
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [includeDemo, setIncludeDemo] = useState(false);
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const cursor = cursors[cursors.length - 1] ?? null;
  const [target, setTarget] = useState<PlatformTenant | null>(null);
  const [reason, setReason] = useState("");

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
    () => apiGet<Page<PlatformTenant>>("/platform/tenants", { q, status: status || undefined, include_demo: includeDemo || undefined, limit: PAGE_SIZE, cursor }),
    [q, status, includeDemo, cursor],
    (page) => page.items.length === 0,
  );

  const change = useSubmit(async (tenant: PlatformTenant, why: string) =>
    tenant.status === "active"
      ? apiPost<PlatformTenant>(`/platform/tenants/${tenant.id}/suspend`, { reason: why })
      : apiPost<PlatformTenant>(`/platform/tenants/${tenant.id}/reactivate`, {}),
  );

  const rows: Row[] = useMemo(
    () =>
      (list.data?.items ?? []).map((t) => ({
        ...t,
        activity: t.last_activity_at ? formatDateTime(t.last_activity_at) : "No activity yet",
        kind: t.is_demo ? "Demo" : t.plan,
        actions: t.status,
      })),
    [list.data],
  );

  const columns: Column<Row>[] = [
    { key: "name", header: "Shop" },
    { key: "kind", header: "Plan" },
    { key: "status", header: "Status", status: true },
    { key: "users", header: "Users", numeric: true },
    { key: "activity", header: "Last activity" },
    {
      key: "actions",
      header: "",
      render: (r) => (
        <Button
          size="sm"
          variant={r.status === "active" ? "danger" : "secondary"}
          onClick={() => {
            setReason("");
            change.clear();
            setTarget(r);
          }}
        >
          {r.status === "active" ? "Suspend" : "Reactivate"}
        </Button>
      ),
    },
  ];

  const suspending = target?.status === "active";
  const reasonOk = !suspending || reason.trim().length >= 3;

  async function onConfirm() {
    if (!target) return;
    const done = await change.run(target, reason.trim());
    if (!done) return;
    toast.success(done.status === "suspended" ? `Suspended ${done.name}` : `Reactivated ${done.name}`);
    setTarget(null);
    list.reload();
  }

  const total = list.data?.total ?? 0;
  const from = rows.length === 0 ? 0 : (cursors.length - 1) * PAGE_SIZE + 1;
  const to = (cursors.length - 1) * PAGE_SIZE + rows.length;
  const filtered = q !== "" || status !== "" || includeDemo;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Shops" description="Every shop on BazaarFlow. Suspending a shop locks its people out at once." />

      <div className="flex flex-wrap items-end gap-3 rounded-card border-2 border-line-strong bg-surface-raised p-5 shadow-card" role="search" aria-label="Filter shops">
        <div className="flex min-w-48 flex-1 flex-col gap-1">
          <label htmlFor="tenant-search" className="text-ui-xs font-medium text-fg-muted">
            Search
          </label>
          <TextInput id="tenant-search" type="search" placeholder="Shop name" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="tenant-status" className="text-ui-xs font-medium text-fg-muted">
            Status
          </label>
          <SelectInput
            id="tenant-status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setCursors([null]);
            }}
          >
            <option value="">Any status</option>
            <option value="active">Active</option>
            <option value="suspended">Suspended</option>
          </SelectInput>
        </div>
        <label className="flex h-control-md items-center gap-2 text-ui-base text-fg">
          <Checkbox
            checked={includeDemo}
            onChange={(e) => {
              setIncludeDemo(e.target.checked);
              setCursors([null]);
            }}
          />
          Include visitor demos
        </label>
      </div>

      <DataTable
        caption="Shops"
        columns={columns}
        rows={rows}
        state={list.state}
        rowKey={(r) => r.id}
        emptyMessage={filtered ? "No shops match these filters." : "No shops have signed up yet."}
        emptyAction={
          filtered
            ? {
                label: "Clear filters",
                onClick: () => {
                  setSearch("");
                  setQ("");
                  setStatus("");
                  setIncludeDemo(false);
                  setCursors([null]);
                },
              }
            : undefined
        }
        errorMessage={list.error?.message ?? "Could not load the shops."}
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

      {target ? (
        <ConfirmDialog
          open
          onOpenChange={(open) => !open && setTarget(null)}
          title={suspending ? `Suspend ${target.name}?` : `Reactivate ${target.name}?`}
          confirmLabel={suspending ? "Suspend shop" : "Reactivate shop"}
          danger={suspending}
          pending={change.pending}
          onConfirm={() => reasonOk && void onConfirm()}
        >
          {suspending ? (
            <div className="flex flex-col gap-2">
              <p>Everyone in this shop is signed out of its pages on their next request, and cannot sign in until you reactivate it.</p>
              <label htmlFor="suspend-reason" className="text-ui-xs font-medium text-fg-muted">
                Reason (kept in the audit log)
              </label>
              <TextInput id="suspend-reason" value={reason} onChange={(e) => setReason(e.target.value)} invalid={reason !== "" && !reasonOk} />
              {!reasonOk ? <p className="text-ui-xs text-fg-muted">Write at least 3 characters.</p> : null}
            </div>
          ) : (
            <p>This shop&apos;s people can sign in again.</p>
          )}
          {change.error ? (
            <p role="alert" className="mt-2 text-danger">
              {change.error.message}
            </p>
          ) : null}
        </ConfirmDialog>
      ) : null}
    </div>
  );
}
