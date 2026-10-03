"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { useState } from "react";
import { Button } from "@/components/app/Button";
import { TextArea } from "@/components/form/Controls";
import { FormField } from "@/components/form/FormField";
import { useSubmit } from "@/hooks/useSubmit";
import { apiPost } from "@/lib/api/client";
import type { Approval } from "@/lib/api/types";

/** Rejecting records why (kept on the approval and in the audit log). Nothing the agent proposed is run. */
export function RejectDialog({
  approval,
  open,
  onOpenChange,
  onRejected,
}: {
  approval: Approval;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRejected: (a: Approval) => void;
}) {
  const [reason, setReason] = useState("");
  const [touched, setTouched] = useState(false);
  const reject = useSubmit((body: { reason: string }) => apiPost<Approval>(`/approvals/${approval.id}/reject`, body));
  const tooShort = reason.trim().length < 3;

  async function confirm() {
    setTouched(true);
    if (tooShort) return;
    const done = await reject.run({ reason: reason.trim() });
    if (done) {
      setReason("");
      setTouched(false);
      onRejected(done);
      onOpenChange(false);
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-fg/40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,28rem)] -translate-x-1/2 -translate-y-1/2 rounded-lg border border-border bg-surface-raised p-4 shadow-popover focus-visible:outline-none">
          <Dialog.Title className="text-ui-md font-semibold text-fg">Reject this request?</Dialog.Title>
          <Dialog.Description className="mt-2 text-ui-base text-fg-muted">{approval.summary}. Nothing will be changed.</Dialog.Description>
          {reject.error ? (
            <p role="alert" className="mt-3 rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
              {reject.error.message}
            </p>
          ) : null}
          <div className="mt-3">
            <FormField id={`reject-${approval.id}`} label="Why are you rejecting it?" required error={touched && tooShort ? "Give a reason of at least 3 characters" : undefined}>
              <TextArea id={`reject-${approval.id}`} rows={2} maxLength={255} value={reason} onChange={(e) => setReason(e.target.value)} onBlur={() => setTouched(true)} invalid={touched && tooShort} />
            </FormField>
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <Dialog.Close asChild>
              <Button>Keep it waiting</Button>
            </Dialog.Close>
            <Button variant="danger" loading={reject.pending} onClick={() => void confirm()}>
              Reject
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
