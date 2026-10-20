"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { Button, buttonClass } from "@/components/app/Button";
import { DataTable, type Column } from "@/components/app/DataTable";
import { PageHeader } from "@/components/app/PageHeader";
import { SelectInput } from "@/components/form/Controls";
import { useLoad } from "@/hooks/useLoad";
import { useSubmit } from "@/hooks/useSubmit";
import { apiGet, apiPost } from "@/lib/api/client";
import type { CommentReply, Page } from "@/lib/api/types";
import { formatDateTime, formatNumber } from "@/lib/format";

const PAGE_SIZE = 25;
const STATUSES = [
  { value: "", label: "Every comment" },
  { value: "proposed", label: "Waiting for approval" },
  { value: "approved", label: "Approved" },
  { value: "posted", label: "Replied" },
  { value: "skipped", label: "Skipped" },
  { value: "failed", label: "Failed" },
];

type Row = CommentReply & { when: string; from: string; actions: string };

/**
 * Facebook comments on your posts and the replies proposed for them (PRD W-004). A reply waits in Approvals unless the
 * posting schedule is on automatic; skipping one here closes its approval. The comment text is shown as plain text.
 */
export function CommentsView() {
  const [status, setStatus] = useState("");
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const cursor = cursors[cursors.length - 1] ?? null;
  const list = useLoad(
    () => apiGet<Page<CommentReply>>("/marketing/comments/", { status: status || undefined, limit: PAGE_SIZE, cursor }),
    [status, cursor],
    (page) => page.items.length === 0,
  );
  const skip = useSubmit((id: string) => apiPost<CommentReply>(`/marketing/comments/${id}/skip`));

  const inFlight = useRef(new Set<string>()); // a second click while the first is still running does nothing

  async function skipReply(id: string) {
    if (inFlight.current.has(id)) return;
    inFlight.current.add(id);
    try {
      const done = await skip.run(id);
      if (done) toast.success("Skipped");
      else if (skip.error) toast.error(skip.error.message);
      list.reload();
    } finally {
      inFlight.current.delete(id);
    }
  }

  const rows: Row[] = (list.data?.items ?? []).map((r) => ({
    ...r,
    when: formatDateTime(r.posted_at ?? r.created_at),
    from: r.author ?? "A visitor",
    actions: r.status,
  }));

  const columns: Column<Row>[] = [
    { key: "post_title", header: "Post" },
    { key: "from", header: "From" },
    { key: "comment_text", header: "Comment" },
    { key: "reply_text", header: "Reply" },
    { key: "status", header: "Status", status: true },
    { key: "when", header: "When" },
    {
      key: "actions",
      header: "",
      render: (r) =>
        r.status === "proposed" || r.status === "approved" ? (
          <Button size="sm" onClick={() => void skipReply(r.id)}>
            Skip
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
        title="Comments"
        description="What people say under your posts, and the replies proposed for them."
        actions={
          <Link href="/approvals" className={buttonClass("secondary")}>
            Approvals
          </Link>
        }
      />
      <div className="flex flex-wrap items-end gap-3 rounded-card border-2 border-line-strong bg-surface-raised p-5 shadow-card" role="search" aria-label="Filter comments">
        <div className="flex flex-col gap-1">
          <label htmlFor="comment-status" className="text-ui-xs font-medium text-fg-muted">
            Show
          </label>
          <SelectInput
            id="comment-status"
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
        caption="Comments"
        columns={columns}
        rows={rows}
        state={list.state}
        rowKey={(r) => r.id}
        emptyMessage={status ? "No comments with this status." : "No comments yet. They appear once your published posts get some."}
        emptyAction={status ? { label: "Clear filter", onClick: () => setStatus("") } : undefined}
        errorMessage={list.error?.message ?? "Could not load comments."}
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
