"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Button } from "@/components/app/Button";
import { DataTable, type Column } from "@/components/app/DataTable";
import { PageHeader } from "@/components/app/PageHeader";
import { RequireRole } from "@/components/app/RequireRole";
import { SelectInput } from "@/components/form/Controls";
import { DraftBriefForm } from "@/components/marketing/DraftBriefForm";
import { useLoad } from "@/hooks/useLoad";
import { apiGet } from "@/lib/api/client";
import type { MarketingPost, Page } from "@/lib/api/types";
import { formatDateTime, formatNumber } from "@/lib/format";

const PAGE_SIZE = 10;

const FILTERS = [
  { value: "", label: "All posts" },
  { value: "draft", label: "Drafts" },
  { value: "pending_approval", label: "Waiting for approval" },
  { value: "approved", label: "Approved" },
];

type Row = MarketingPost & { when: string; shown: string };

function Studio() {
  const [status, setStatus] = useState("");
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const cursor = cursors[cursors.length - 1] ?? null;
  const list = useLoad(
    () => apiGet<Page<MarketingPost>>("/marketing/posts/", { status, limit: PAGE_SIZE, cursor }),
    [status, cursor],
    (page) => page.items.length === 0,
  );

  const rows: Row[] = useMemo(() => (list.data?.items ?? []).map((p) => ({ ...p, when: formatDateTime(p.updated_at), shown: p.status })), [list.data]);
  const columns: Column<Row>[] = [
    {
      key: "title",
      header: "Title",
      render: (r) => (
        <Link href={`/marketing/${r.id}`} className="font-medium text-action hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-focus">
          {r.title}
        </Link>
      ),
    },
    { key: "shown", header: "Status", status: true },
    { key: "when", header: "Last changed" },
  ];

  const total = list.data?.total ?? 0;
  const from = rows.length === 0 ? 0 : (cursors.length - 1) * PAGE_SIZE + 1;
  const to = (cursors.length - 1) * PAGE_SIZE + rows.length;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Marketing studio" description="Ask the assistant for a post, make it yours, then send it for approval." />
      <DraftBriefForm />

      <section aria-label="Your posts" className="flex flex-col gap-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 className="text-ui-md font-semibold text-fg">Your posts</h2>
          <div className="flex flex-col gap-1">
            <label htmlFor="post-status" className="text-ui-xs font-medium text-fg-muted">
              Show
            </label>
            <SelectInput
              id="post-status"
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setCursors([null]);
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
        <DataTable
          caption="Marketing posts"
          columns={columns}
          rows={rows}
          state={list.state}
          rowKey={(r) => r.id}
          emptyMessage={status ? "No posts have this status." : "No posts yet. Draft your first one above."}
          emptyAction={status ? { label: "Show all posts", onClick: () => setStatus("") } : undefined}
          errorMessage={list.error?.message ?? "Could not load your posts."}
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
      </section>
    </div>
  );
}

/** Marketing studio (PRD F-014). Owners and managers only. */
export default function MarketingStudioPage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <Studio />
    </RequireRole>
  );
}
