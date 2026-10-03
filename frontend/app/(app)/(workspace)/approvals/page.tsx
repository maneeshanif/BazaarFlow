"use client";

import { useState } from "react";
import { ApprovalCard } from "@/components/agent/ApprovalCard";
import { Button } from "@/components/app/Button";
import { PageHeader } from "@/components/app/PageHeader";
import { RequireRole } from "@/components/app/RequireRole";
import { EmptyState, ErrorState, UnauthorizedState } from "@/components/app/StateViews";
import { SelectInput } from "@/components/form/Controls";
import { Skeleton } from "@/components/ui/skeleton";
import { useLoad } from "@/hooks/useLoad";
import { apiGet } from "@/lib/api/client";
import type { Approval, Page } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";

const PAGE_SIZE = 10;

const FILTERS = [
  { value: "pending", label: "Waiting for you" },
  { value: "executed", label: "Approved and done" },
  { value: "rejected", label: "Rejected" },
  { value: "failed", label: "Could not run" },
  { value: "expired", label: "Expired" },
  { value: "", label: "Everything" },
];

const EMPTY: Record<string, string> = {
  pending: "Nothing is waiting for your approval.",
  executed: "Nothing has been approved yet.",
  rejected: "Nothing has been rejected.",
  failed: "Nothing failed to run.",
  expired: "Nothing has expired.",
  "": "The agent has not proposed anything yet.",
};

function ApprovalsList() {
  const [status, setStatus] = useState("pending");
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const [changed, setChanged] = useState<Record<string, Approval>>({});
  const cursor = cursors[cursors.length - 1] ?? null;
  const list = useLoad(
    () => apiGet<Page<Approval>>("/approvals/", { status, limit: PAGE_SIZE, cursor }),
    [status, cursor],
    (page) => page.items.length === 0,
  );

  const total = list.data?.total ?? 0;
  const from = (list.data?.items.length ?? 0) === 0 ? 0 : (cursors.length - 1) * PAGE_SIZE + 1;
  const to = (cursors.length - 1) * PAGE_SIZE + (list.data?.items.length ?? 0);

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Approvals" description="What the AI assistant wants to do. Nothing changes until you approve it." />
      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-surface p-3" role="search" aria-label="Filter approvals">
        <div className="flex flex-col gap-1">
          <label htmlFor="approval-status" className="text-ui-xs font-medium text-fg-muted">
            Show
          </label>
          <SelectInput
            id="approval-status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setCursors([null]);
              setChanged({});
            }}
          >
            {FILTERS.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </SelectInput>
        </div>
      </div>

      {list.state === "loading" ? (
        <div role="status" aria-busy="true" aria-label="Loading approvals" className="flex flex-col gap-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
      ) : null}
      {list.state === "error" ? <ErrorState message={list.error?.message ?? "Could not load approvals."} onRetry={list.reload} /> : null}
      {list.state === "unauthorized" ? <UnauthorizedState /> : null}
      {list.state === "empty" ? (
        <div className="rounded-lg border border-border bg-surface">
          <EmptyState message={EMPTY[status] ?? "Nothing here."} />
        </div>
      ) : null}
      {list.state === "ready" ? (
        <>
          <ul className="flex flex-col gap-3">
            {(list.data?.items ?? []).map((a) => (
              <li key={a.id}>
                <ApprovalCard approval={changed[a.id] ?? a} canDecide onChanged={(next) => setChanged((c) => ({ ...c, [a.id]: next }))} />
              </li>
            ))}
          </ul>
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
        </>
      ) : null}
    </div>
  );
}

/** The approvals center (PRD F-021). Owners and managers only. */
export default function ApprovalsPage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <ApprovalsList />
    </RequireRole>
  );
}
