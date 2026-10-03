"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { AgentStatusPanel } from "@/components/agent/AgentStatusPanel";
import { Button } from "@/components/app/Button";
import { DataTable, type Column } from "@/components/app/DataTable";
import { PageHeader } from "@/components/app/PageHeader";
import { RequireRole } from "@/components/app/RequireRole";
import { SelectInput } from "@/components/form/Controls";
import { useLoad } from "@/hooks/useLoad";
import { apiGet } from "@/lib/api/client";
import type { AgentRun, AgentStatus, Page } from "@/lib/api/types";
import { formatDateTime, formatNumber } from "@/lib/format";

const PAGE_SIZE = 25;

const OUTCOMES = [
  { value: "", label: "Any result" },
  { value: "ok", label: "Completed" },
  { value: "failed", label: "Failed" },
  { value: "step_limit", label: "Stopped: too many steps" },
  { value: "spend_limit", label: "Stopped: allowance used" },
  { value: "paused", label: "Paused" },
];

type Row = AgentRun & { when: string; who: string; asked: string; result: string; cost: string; actions: string };

const short = (text: string, max = 70): string => (text.length > max ? `${text.slice(0, max - 1)}…` : text);

function Activity() {
  const [outcome, setOutcome] = useState("");
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const cursor = cursors[cursors.length - 1] ?? null;
  const [statusOverride, setStatusOverride] = useState<AgentStatus | null>(null);

  const status = useLoad(() => apiGet<AgentStatus>("/agent-runs/status"), []);
  const list = useLoad(
    () => apiGet<Page<AgentRun>>("/agent-runs/", { outcome, limit: PAGE_SIZE, cursor }),
    [outcome, cursor],
    (page) => page.items.length === 0,
  );

  const rows: Row[] = useMemo(
    () =>
      (list.data?.items ?? []).map((r) => ({
        ...r,
        when: formatDateTime(r.created_at),
        who: r.user_name ?? "System",
        asked: short(r.input_text),
        result: r.outcome === "ok" ? "completed" : r.outcome,
        cost: `$${r.spend_usd}`,
        actions: String(r.action_ids.length),
      })),
    [list.data],
  );

  const columns: Column<Row>[] = [
    {
      key: "when",
      header: "When",
      render: (r) => (
        <Link href={`/agent-activity/${r.id}`} className="font-medium text-action hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-focus">
          {r.when}
        </Link>
      ),
    },
    { key: "who", header: "Who asked" },
    { key: "asked", header: "What they said" },
    { key: "result", header: "Result", status: true },
    { key: "actions", header: "Requests filed", numeric: true },
    { key: "tokens_in", header: "Tokens in", numeric: true },
    { key: "tokens_out", header: "Tokens out", numeric: true },
    { key: "cost", header: "Cost", mono: true },
  ];

  const total = list.data?.total ?? 0;
  const from = rows.length === 0 ? 0 : (cursors.length - 1) * PAGE_SIZE + 1;
  const to = (cursors.length - 1) * PAGE_SIZE + rows.length;
  const shown = statusOverride ?? status.data;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Agent activity" description="Every conversation the AI assistant handled: who asked, what it did, and what it cost." />
      {shown ? <AgentStatusPanel status={shown} onChanged={setStatusOverride} /> : null}
      {status.state === "error" ? (
        <p role="alert" className="rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
          {status.error?.message ?? "Could not load the assistant status."}
        </p>
      ) : null}

      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-surface p-3" role="search" aria-label="Filter activity">
        <div className="flex flex-col gap-1">
          <label htmlFor="run-outcome" className="text-ui-xs font-medium text-fg-muted">
            Result
          </label>
          <SelectInput
            id="run-outcome"
            value={outcome}
            onChange={(e) => {
              setOutcome(e.target.value);
              setCursors([null]);
            }}
          >
            {OUTCOMES.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </SelectInput>
        </div>
      </div>

      <DataTable
        caption="Agent runs"
        columns={columns}
        rows={rows}
        state={list.state}
        rowKey={(r) => r.id}
        emptyMessage={outcome ? "No runs have this result." : "The assistant has not handled any conversations yet."}
        emptyAction={outcome ? { label: "Clear filter", onClick: () => setOutcome("") } : undefined}
        errorMessage={list.error?.message ?? "Could not load the activity."}
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

/** The agent activity log (PRD F-022). Owners and managers only. */
export default function AgentActivityPage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <Activity />
    </RequireRole>
  );
}
