"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { useState } from "react";
import { Button } from "@/components/app/Button";
import { TextArea } from "@/components/form/Controls";
import { FormField } from "@/components/form/FormField";
import { useSubmit } from "@/hooks/useSubmit";
import { apiPost } from "@/lib/api/client";
import type { OrderDetail } from "@/lib/api/types";
import { formatMoney } from "@/lib/format";

/** Reversing a posted sale needs a reason (kept on the order and in the audit log) and an explicit confirmation. */
export function ReverseDialog({ order, open, onOpenChange, onReversed }: { order: OrderDetail; open: boolean; onOpenChange: (open: boolean) => void; onReversed: (o: OrderDetail) => void }) {
  const [reason, setReason] = useState("");
  const [touched, setTouched] = useState(false);
  const reverse = useSubmit((body: { reason: string }) => apiPost<OrderDetail>(`/orders/${order.id}/reverse`, body));
  const tooShort = reason.trim().length < 3;

  async function confirm() {
    setTouched(true);
    if (tooShort) return;
    const done = await reverse.run({ reason: reason.trim() });
    if (done) {
      setReason("");
      setTouched(false);
      onReversed(done);
      onOpenChange(false);
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-fg/40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,30rem)] -translate-x-1/2 -translate-y-1/2 rounded-lg border border-border bg-surface-raised p-4 shadow-popover focus-visible:outline-none">
          <Dialog.Title className="text-ui-md font-semibold text-fg">Reverse this sale?</Dialog.Title>
          <Dialog.Description className="mt-2 text-ui-base text-fg-muted">
            The {order.item_count === 1 ? "item goes" : `${order.item_count} items go`} back into stock, the payment is marked reversed
            {order.amount_due !== "0.00" ? ` and ${formatMoney(order.amount_due)} comes off what ${order.customer_name ?? "the customer"} owes` : ""}. The sale stays on record as
            reversed. This cannot be undone.
          </Dialog.Description>
          {reverse.error ? (
            <p role="alert" className="mt-3 rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
              {reverse.error.message}
            </p>
          ) : null}
          <div className="mt-3">
            <FormField id="reverse-reason" label="Why is it being reversed?" required error={touched && tooShort ? "Give a reason of at least 3 characters" : undefined}>
              <TextArea id="reverse-reason" rows={2} maxLength={255} value={reason} onChange={(e) => setReason(e.target.value)} onBlur={() => setTouched(true)} invalid={touched && tooShort} />
            </FormField>
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <Dialog.Close asChild>
              <Button>Keep the sale</Button>
            </Dialog.Close>
            <Button variant="danger" loading={reverse.pending} onClick={() => void confirm()}>
              Reverse sale
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
