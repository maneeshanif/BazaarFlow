"use client";

import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Button, buttonClass } from "@/components/app/Button";
import { DataTable, type Column } from "@/components/app/DataTable";
import { PageHeader } from "@/components/app/PageHeader";
import { SelectInput } from "@/components/form/Controls";
import { useLoad } from "@/hooks/useLoad";
import { useSubmit } from "@/hooks/useSubmit";
import { apiGet, apiPost } from "@/lib/api/client";
import type { MarketingActivity, Page } from "@/lib/api/types";
import { formatDateTime, formatNumber } from "@/lib/format";

const PAGE_SIZE = 25;
const STATUSES = [
  { value: "", label: "Every post" },
  { value: "pending_approval", label: "Waiting for approval" },
  { value: "approved", label: "Approved" },
  { value: "queued", label: "Queued" },
  { value: "published", label: "Published" },
  { value: "failed", label: "Failed" },
  { value: "cancelled", label: "Cancelled" },
];

type Row = MarketingActivity & { when: string; origin: string; reason: string; actions: string };

/** Marketing activity (PRD F-016): every post on its way to Facebook, what happened, and a Retry for the ones that failed. */
export function ActivityView() {
  const [status, setStatus] = useState("");
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const cursor = cursors[cursors.length - 1] ?? null;
  const list = useLoad(
    () => apiGet<Page<MarketingActivity>>("/marketing/activity", { status: status || undefined, limit: PAGE_SIZE, cursor }),
    [status, cursor],
    (page) => page.items.length === 0,
  );
  const act = useSubmit((id: string, action: "retry" | "cancel") => apiPost<MarketingActivity>(`/marketing/activity/${id}/${action}`));

  async function run(id: string, action: "retry" | "cancel") {
    const done = await act.run(id, action);
    if (done) toast.success(action === "retry" ? "Queued again" : "Cancelled");
    else if (act.error) toast.error(act.error.message);
    list.reload();
  }

  const rows: Row[] = (list.data?.items ?? []).map((p) => ({
    ...p,
    when: formatDateTime(p.published_at ?? p.scheduled_for ?? p.created_at),
    origin: p.source === "schedule" ? "Schedule" : "Studio",
    reason: p.last_error ?? "",
    actions: p.status,
  }));

  const columns: Column<Row>[] = [
    { key: "title", header: "Post" },
    { key: "status", header: "Status", status: true },
    { key: "when", header: "When" },
    { key: "origin", header: "From" },
    { key: "attempts", header: "Tries", numeric: true },
    { key: "reason", header: "What went wrong" },
    {
      key: "actions",
      header: "",
      render: (r) =>
        r.status === "failed" ? (
          <Button size="sm" onClick={() => void run(r.id, "retry")}>
            Retry
          </Button>
        ) : r.status === "queued" || r.status === "approved" ? (
          <Button size="sm" variant="danger" onClick={() => void run(r.id, "cancel")}>
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
      <PageHeader
        title="Marketing activity"
        description="Every post on its way to Facebook, and what happened to it."
        actions={
          <Link href="/marketing/schedule" className={buttonClass("secondary")}>
            Posting schedule
          </Link>
        }
      />
      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-surface p-3" role="search" aria-label="Filter posts">
        <div className="flex flex-col gap-1">
          <label htmlFor="activity-status" className="text-ui-xs font-medium text-fg-muted">
            Show
          </label>
          <SelectInput
            id="activity-status"
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
        caption="Marketing activity"
        columns={columns}
        rows={rows}
        state={list.state}
        rowKey={(r) => r.id}
        emptyMessage={status ? "No posts with this status." : "No posts yet. Switch on the posting schedule or write one in the studio."}
        emptyAction={status ? { label: "Clear filter", onClick: () => setStatus("") } : undefined}
        errorMessage={list.error?.message ?? "Could not load marketing activity."}
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
