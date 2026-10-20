"use client";

import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Button } from "@/components/app/Button";
import { DataTable, type Column } from "@/components/app/DataTable";
import { PageHeader } from "@/components/app/PageHeader";
import { SelectInput, TextInput } from "@/components/form/Controls";
import { useLoad } from "@/hooks/useLoad";
import { apiGet } from "@/lib/api/client";
import type { Page, SystemLog, SystemLogDetail } from "@/lib/api/types";
import { formatDateTime, formatNumber } from "@/lib/format";

const PAGE_SIZE = 50;

type Row = SystemLog & { when: string; shop: string; open: string };

function Detail({ id, onClose }: { id: string; onClose: () => void }) {
  const loaded = useLoad(() => apiGet<SystemLogDetail>(`/platform/logs/${id}`), [id]);
  return (
    <Dialog.Root open onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-fg/40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[80vh] w-[min(92vw,40rem)] -translate-x-1/2 -translate-y-1/2 overflow-auto rounded-card border-2 border-line-strong bg-surface-raised-raised p-4 shadow-popover focus-visible:outline-none">
          <Dialog.Title className="text-ui-md font-semibold text-fg">{loaded.data?.action ?? "Log entry"}</Dialog.Title>
          <Dialog.Description className="text-ui-sm text-fg-muted">Secrets are masked when a log entry is written.</Dialog.Description>
          {loaded.state === "error" ? <p role="alert" className="mt-2 text-danger">{loaded.error?.message}</p> : null}
          {loaded.data ? (
            <pre className="mt-3 overflow-auto rounded-md bg-surface-sunken p-3 font-mono text-ui-xs text-fg">
              {JSON.stringify({ shop: loaded.data.tenant_name, actor: `${loaded.data.actor_type} ${loaded.data.actor_id ?? ""}`.trim(), entity: loaded.data.entity, entity_id: loaded.data.entity_id, request_id: loaded.data.request_id, before: loaded.data.before, after: loaded.data.after }, null, 2)}
            </pre>
          ) : null}
          <div className="mt-3 flex justify-end">
            <Dialog.Close asChild>
              <Button>Close</Button>
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/** System logs (PRD F-028): the audit trail across shops. BazaarFlow operators only; read-only. */
export function LogsView() {
  const [search, setSearch] = useState("");
  const [action, setAction] = useState("");
  const [actor, setActor] = useState("");
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const [opened, setOpened] = useState<string | null>(null);
  const cursor = cursors[cursors.length - 1] ?? null;

  useEffect(() => {
    const next = search.trim();
    if (next === action) return;
    const id = setTimeout(() => {
      setAction(next);
      setCursors([null]);
    }, 300);
    return () => clearTimeout(id);
  }, [search, action]);

  const list = useLoad(
    () => apiGet<Page<SystemLog>>("/platform/logs", { action: action || undefined, actor_type: actor || undefined, limit: PAGE_SIZE, cursor }),
    [action, actor, cursor],
    (page) => page.items.length === 0,
  );
  const rows: Row[] = (list.data?.items ?? []).map((l) => ({ ...l, when: formatDateTime(l.created_at), shop: l.tenant_name ?? "Platform", open: l.id }));
  const columns: Column<Row>[] = [
    { key: "when", header: "When" },
    { key: "shop", header: "Shop" },
    { key: "actor_type", header: "By" },
    { key: "action", header: "What happened", mono: true },
    { key: "entity", header: "On" },
    { key: "open", header: "", render: (r) => <Button size="sm" onClick={() => setOpened(r.id)}>Details</Button> },
  ];
  const total = list.data?.total ?? 0;
  const from = rows.length === 0 ? 0 : (cursors.length - 1) * PAGE_SIZE + 1;
  const to = (cursors.length - 1) * PAGE_SIZE + rows.length;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="System logs" description="The audit trail across every shop, newest first. It cannot be changed." />
      <div className="flex flex-wrap items-end gap-3 rounded-card border-2 border-line-strong bg-surface-raised p-5 shadow-card" role="search" aria-label="Filter logs">
        <div className="flex min-w-48 flex-1 flex-col gap-1">
          <label htmlFor="log-action" className="text-ui-xs font-medium text-fg-muted">Action contains</label>
          <TextInput id="log-action" type="search" placeholder="for example login or integration" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="log-actor" className="text-ui-xs font-medium text-fg-muted">By</label>
          <SelectInput id="log-actor" value={actor} onChange={(e) => { setActor(e.target.value); setCursors([null]); }}>
            <option value="">Anyone</option>
            <option value="user">A person</option>
            <option value="agent">The AI</option>
            <option value="system">The system</option>
          </SelectInput>
        </div>
      </div>
      <DataTable
        caption="System logs"
        columns={columns}
        rows={rows}
        state={list.state}
        rowKey={(r) => r.id}
        emptyMessage={action || actor ? "No log entries match." : "Nothing has been logged yet."}
        errorMessage={list.error?.message ?? "Could not load the logs."}
        onRetry={list.reload}
      />
      {list.state === "ready" ? (
        <nav aria-label="Pagination" className="flex items-center justify-between gap-2 text-ui-sm text-fg-muted">
          <span>Showing {formatNumber(from)} to {formatNumber(to)} of {formatNumber(total)}</span>
          <span className="flex gap-2">
            <Button size="sm" disabled={cursors.length === 1} onClick={() => setCursors((c) => c.slice(0, -1))}>Previous</Button>
            <Button size="sm" disabled={!list.data?.next_cursor} onClick={() => list.data?.next_cursor && setCursors((c) => [...c, list.data?.next_cursor ?? null])}>Next</Button>
          </span>
        </nav>
      ) : null}
      {opened ? <Detail id={opened} onClose={() => setOpened(null)} /> : null}
    </div>
  );
}
