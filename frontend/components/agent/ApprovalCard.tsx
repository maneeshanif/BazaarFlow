"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/app/Button";
import { StatusBadge } from "@/components/app/StatusBadge";
import { EditApprovalDialog } from "@/components/agent/EditApprovalDialog";
import { RejectDialog } from "@/components/agent/RejectDialog";
import { useSubmit } from "@/hooks/useSubmit";
import { apiPost } from "@/lib/api/client";
import type { Approval } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";

const KIND: Record<string, string> = { post_order: "Sale", record_payment: "Payment", adjust_stock: "Stock change", approve_post: "Marketing post" };

/**
 * One thing an agent wants to do (PRD F-021): what it is in plain words, who asked, and Approve / Edit / Reject for
 * a manager or owner. Approving runs exactly the stored proposal; if the rules now refuse it, it is marked failed with
 * the reason and nothing changes. Used in the Approvals page and inline in the sales chat.
 */
export function ApprovalCard({ approval, canDecide, onChanged, className }: { approval: Approval; canDecide: boolean; onChanged: (a: Approval) => void; className?: string }) {
  const [rejecting, setRejecting] = useState(false);
  const [editing, setEditing] = useState(false);
  const approve = useSubmit(() => apiPost<Approval>(`/approvals/${approval.id}/approve`));
  const pending = approval.status === "pending";
  const editable = approval.tool !== "approve_post"; // a post is edited in the studio, not here

  async function onApprove() {
    const done = await approve.run();
    if (!done) return;
    onChanged(done);
    if (done.status === "executed") toast.success(`Approved: ${done.summary}`);
    else toast.error(`Could not run it: ${done.decision_note ?? done.status}`);
  }

  return (
    <article aria-label={`${KIND[approval.tool] ?? "Request"}: ${approval.summary}`} className={cn("rounded-lg border border-border bg-surface p-4", className)}>
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-ui-base font-semibold text-fg">{KIND[approval.tool] ?? approval.tool}</h3>
        <StatusBadge status={approval.status} />
      </header>
      <p className="mt-1 text-ui-base text-fg">{approval.summary}</p>
      {approval.details.length > 0 ? (
        <ul className="mt-2 list-disc pl-5 text-ui-sm text-fg-muted">
          {approval.details.map((d, i) => (
            <li key={`${i}-${d}`} className={d.startsWith("Problem:") ? "text-danger" : undefined}>
              {d}
            </li>
          ))}
        </ul>
      ) : null}
      <p className="mt-2 text-ui-xs text-fg-subtle">
        Asked {formatDateTime(approval.created_at)}
        {approval.requested_by_name ? ` by ${approval.requested_by_name}` : ""}
        {pending && approval.expires_at ? `. Expires ${formatDateTime(approval.expires_at)}` : ""}
      </p>
      {approval.decision_note && !pending ? (
        <p role={approval.status === "failed" ? "alert" : undefined} className={cn("mt-2 text-ui-sm", approval.status === "failed" ? "text-danger" : "text-fg-muted")}>
          {approval.decision_note}
        </p>
      ) : null}
      {approve.error ? (
        <p role="alert" className="mt-2 rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
          {approve.error.message}
        </p>
      ) : null}
      {pending && canDecide ? (
        <div className="mt-3 flex flex-wrap justify-end gap-2">
          <Button onClick={() => setRejecting(true)}>Reject</Button>
          {editable ? <Button onClick={() => setEditing(true)}>Edit</Button> : null}
          <Button variant="primary" loading={approve.pending} onClick={() => void onApprove()}>
            Approve
          </Button>
        </div>
      ) : null}
      {pending && !canDecide ? <p className="mt-2 text-ui-sm text-fg-muted">Waiting for a manager or the owner to approve it.</p> : null}
      {canDecide ? (
        <>
          <RejectDialog approval={approval} open={rejecting} onOpenChange={setRejecting} onRejected={onChanged} />
          {editable ? <EditApprovalDialog key={JSON.stringify(approval.payload)} approval={approval} open={editing} onOpenChange={setEditing} onEdited={onChanged} /> : null}
        </>
      ) : null}
    </article>
  );
}
