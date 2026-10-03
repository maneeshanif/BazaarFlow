"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { useState } from "react";
import { Button } from "@/components/app/Button";
import { TextInput } from "@/components/form/Controls";
import { FormField } from "@/components/form/FormField";
import { useSubmit } from "@/hooks/useSubmit";
import { apiPatch } from "@/lib/api/client";
import type { Approval } from "@/lib/api/types";

type Item = { product_id: string; qty: number; unit_price?: string | null };

const WHOLE = /^[1-9]\d{0,6}$/;
const NONZERO = /^-?[1-9]\d{0,6}$/;
const MONEY = /^\d{1,12}(\.\d{1,2})?$/;

/** Change a proposal before approving it: quantities of a sale, the amount of a payment, the size of a stock change. */
export function EditApprovalDialog({ approval, open, onOpenChange, onEdited }: { approval: Approval; open: boolean; onOpenChange: (open: boolean) => void; onEdited: (a: Approval) => void }) {
  const payload = approval.payload as Record<string, unknown>;
  const items = (payload.items as Item[] | undefined) ?? [];
  const [qtys, setQtys] = useState<string[]>(items.map((i) => String(i.qty)));
  const [amount, setAmount] = useState(String(payload.amount ?? ""));
  const [delta, setDelta] = useState(String(payload.delta ?? ""));
  const [error, setError] = useState<string | null>(null);
  const save = useSubmit((next: Record<string, unknown>) => apiPatch<Approval>(`/approvals/${approval.id}`, { payload: next }));

  async function confirm() {
    setError(null);
    let next: Record<string, unknown>;
    if (approval.tool === "post_order") {
      if (!qtys.every((q) => WHOLE.test(q.trim()))) return setError("Each quantity must be a whole number above zero.");
      next = { ...payload, items: items.map((item, i) => ({ ...item, qty: Number(qtys[i]) })) };
    } else if (approval.tool === "record_payment") {
      if (!MONEY.test(amount.trim()) || Number(amount) <= 0) return setError("Enter an amount above zero, like 500 or 500.50.");
      next = { ...payload, amount: amount.trim() };
    } else {
      if (!NONZERO.test(delta.trim())) return setError("Enter a whole number other than zero. Use a minus sign to take stock out.");
      next = { ...payload, delta: Number(delta) };
    }
    const done = await save.run(next);
    if (done) {
      onEdited(done);
      onOpenChange(false);
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-fg/40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,28rem)] -translate-x-1/2 -translate-y-1/2 rounded-lg border border-border bg-surface-raised p-4 shadow-popover focus-visible:outline-none">
          <Dialog.Title className="text-ui-md font-semibold text-fg">Edit before approving</Dialog.Title>
          <Dialog.Description className="mt-1 text-ui-sm text-fg-muted">{approval.summary}. It is checked again like a new request when you save.</Dialog.Description>
          {error || save.error ? (
            <p role="alert" className="mt-3 rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
              {error ?? save.error?.message}
            </p>
          ) : null}
          <div className="mt-3 flex flex-col gap-3">
            {approval.tool === "post_order"
              ? items.map((item, i) => (
                  <FormField key={`${item.product_id}-${i}`} id={`edit-qty-${i}`} label={`Quantity: ${approval.details[i] ?? `item ${i + 1}`}`}>
                    <TextInput id={`edit-qty-${i}`} inputMode="numeric" value={qtys[i] ?? ""} onChange={(e) => setQtys((q) => q.map((v, j) => (j === i ? e.target.value : v)))} className="text-right font-mono tabular-nums" />
                  </FormField>
                ))
              : null}
            {approval.tool === "record_payment" ? (
              <FormField id="edit-amount" label="Amount received (Rs)">
                <TextInput id="edit-amount" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} className="text-right font-mono tabular-nums" />
              </FormField>
            ) : null}
            {approval.tool === "adjust_stock" ? (
              <FormField id="edit-delta" label="Quantity change" hint="Use a minus sign to take stock out.">
                <TextInput id="edit-delta" inputMode="numeric" value={delta} onChange={(e) => setDelta(e.target.value)} className="text-right font-mono tabular-nums" />
              </FormField>
            ) : null}
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <Dialog.Close asChild>
              <Button>Cancel</Button>
            </Dialog.Close>
            <Button variant="primary" loading={save.pending} onClick={() => void confirm()}>
              Save changes
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
