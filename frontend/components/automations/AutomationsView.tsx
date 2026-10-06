"use client";

import Link from "next/link";
import { toast } from "sonner";
import { Button } from "@/components/app/Button";
import { DataTable, type Column } from "@/components/app/DataTable";
import { PageHeader } from "@/components/app/PageHeader";
import { ErrorState } from "@/components/app/StateViews";
import { StatusBadge } from "@/components/app/StatusBadge";
import { Skeleton } from "@/components/ui/skeleton";
import { useLoad } from "@/hooks/useLoad";
import { useSubmit } from "@/hooks/useSubmit";
import { apiGet, apiPost } from "@/lib/api/client";
import type { Automation, AutomationRunRow, Page } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

function Recipe({ automation, onChanged }: { automation: Automation; onChanged: () => void }) {
  const toggle = useSubmit((enabled: boolean) => apiPost<Automation>(`/automations/${automation.key}/toggle`, { enabled }));
  const run = useSubmit(() => apiPost<AutomationRunRow>(`/automations/${automation.key}/run`));
  const blocked = !automation.enabled && !automation.requirements_met;

  async function onToggle() {
    const done = await toggle.run(!automation.enabled);
    if (done) {
      toast.success(done.enabled ? "Switched on" : "Switched off");
      onChanged();
    }
  }
  async function onRun() {
    const done = await run.run();
    if (done) {
      toast[done.status === "succeeded" ? "success" : "error"](done.summary ?? done.error ?? "Done");
      onChanged();
    }
  }

  return (
    <li className="rounded-lg border border-border bg-surface p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h2 className="text-ui-md font-semibold text-fg">{automation.label}</h2>
          <p className="max-w-prose text-ui-sm text-fg-muted">{automation.description}</p>
        </div>
        <StatusBadge status={automation.enabled ? "active" : "disabled"} label={automation.enabled ? "on" : "off"} />
      </div>
      {automation.needs_attention ? (
        <p role="alert" className="mt-3 rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
          This has failed {automation.consecutive_failures} times in a row: {automation.last_run?.error ?? "check the history below"}. It keeps trying.
        </p>
      ) : null}
      {blocked ? (
        <p className="mt-3 text-ui-sm text-fg-muted">
          Needs WhatsApp.{" "}
          <Link href="/integrations" className="font-medium text-action hover:underline">
            Connect it first
          </Link>
          .
        </p>
      ) : null}
      {automation.last_run ? (
        <p className="mt-3 text-ui-sm text-fg-muted">
          Last run: {automation.last_run.status === "failed" ? (automation.last_run.error ?? "failed") : (automation.last_run.summary ?? "done")}
          {automation.last_run.finished_at ? ` (${formatDateTime(automation.last_run.finished_at)})` : ""}
        </p>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-2">
        <Button variant={automation.enabled ? "secondary" : "primary"} loading={toggle.pending} disabled={blocked} onClick={() => void onToggle()}>
          {automation.enabled ? "Switch off" : "Switch on"}
        </Button>
        {automation.enabled ? (
          <Button loading={run.pending} onClick={() => void onRun()}>
            Run now
          </Button>
        ) : null}
      </div>
      {toggle.error || run.error ? (
        <p role="alert" className="mt-2 text-ui-sm text-danger">
          {toggle.error?.message ?? run.error?.message}
        </p>
      ) : null}
    </li>
  );
}

type Row = AutomationRunRow & { when: string; reason: string };
const columns: Column<Row>[] = [
  { key: "when", header: "When" },
  { key: "label", header: "Automation" },
  { key: "status", header: "Result", status: true },
  { key: "trigger_source", header: "Started by" },
  { key: "reason", header: "What happened" },
];

/** Automation recipes (PRD F-024): switch the pre-built recipes on or off, run one now, and read what they did. */
export function AutomationsView() {
  const list = useLoad(() => apiGet<Automation[]>("/automations/"), []);
  const runs = useLoad(() => apiGet<Page<AutomationRunRow>>("/automations/runs", { limit: 20 }), [], (p) => p.items.length === 0);
  const reload = () => {
    list.reload();
    runs.reload();
  };
  const rows: Row[] = (runs.data?.items ?? []).map((r) => ({ ...r, when: formatDateTime(r.started_at), reason: r.error ?? r.summary ?? "" }));

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Automations" description="Ready-made routines that save you time. Anything that spends money or sends something to a customer asks you first." />
      {list.state === "loading" ? <Skeleton className="h-40 max-w-form" /> : null}
      {list.state === "error" ? <ErrorState message={list.error?.message ?? "Could not load the automations."} onRetry={list.reload} /> : null}
      {list.data ? (
        <ul className="flex max-w-form flex-col gap-3">
          {list.data.map((a) => (
            <Recipe key={`${a.key}-${a.enabled}-${a.consecutive_failures}`} automation={a} onChanged={reload} />
          ))}
        </ul>
      ) : null}
      <section aria-label="Run history" className="flex flex-col gap-2">
        <h2 className="text-ui-md font-semibold text-fg">Run history</h2>
        <DataTable
          caption="Automation runs"
          columns={columns}
          rows={rows}
          state={runs.state}
          rowKey={(r) => r.id}
          emptyMessage="Nothing has run yet. Switch a recipe on and its runs appear here."
          errorMessage={runs.error?.message ?? "Could not load the history."}
          onRetry={runs.reload}
        />
      </section>
    </div>
  );
}
