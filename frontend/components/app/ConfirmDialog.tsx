"use client";

import * as Dialog from "@radix-ui/react-dialog";
import type { ReactNode } from "react";
import { Button } from "@/components/app/Button";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** names the specific record, e.g. "Delete Classic Shirt?" (ui-rules.md: destructive actions are confirmed) */
  title: string;
  /** what will happen, in plain words */
  children: ReactNode;
  confirmLabel: string;
  onConfirm: () => void;
  pending?: boolean;
  danger?: boolean;
};

/** Blocking confirmation for destructive actions. The confirm button is disabled while the request runs. */
export function ConfirmDialog({ open, onOpenChange, title, children, confirmLabel, onConfirm, pending, danger = true }: Props) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-fg/40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,28rem)] -translate-x-1/2 -translate-y-1/2 rounded-lg border border-border bg-surface-raised p-4 shadow-popover focus-visible:outline-none">
          <Dialog.Title className="text-ui-md font-semibold text-fg">{title}</Dialog.Title>
          <Dialog.Description asChild>
            <div className="mt-2 text-ui-base text-fg-muted">{children}</div>
          </Dialog.Description>
          <div className="mt-4 flex justify-end gap-2">
            <Dialog.Close asChild>
              <Button>Cancel</Button>
            </Dialog.Close>
            <Button variant={danger ? "danger" : "primary"} loading={pending} onClick={onConfirm}>
              {confirmLabel}
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
