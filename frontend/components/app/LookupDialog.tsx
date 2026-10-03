"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Button } from "@/components/app/Button";
import { TextInput } from "@/components/form/Controls";
import { toApiError } from "@/lib/api/client";

type Props<T> = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  placeholder: string;
  /** load the matches for what was typed; called with "" first so a short list shows straight away */
  load: (query: string) => Promise<T[]>;
  keyOf: (item: T) => string;
  render: (item: T) => ReactNode;
  onSelect: (item: T) => void;
  emptyMessage: string;
  /** extra content under the results, e.g. "Add a new customer" */
  footer?: ReactNode;
};

/**
 * The standard search dialog for lookup fields (ui-rules.md "Forms & Validation": a big master list is never a plain
 * select). Type to search; pick a result with the mouse or with Tab and Enter.
 */
export function LookupDialog<T>({ open, onOpenChange, title, description, placeholder, load, keyOf, render, onSelect, emptyMessage, footer }: Props<T>) {
  const [query, setQuery] = useState("");
  // the outcome of the latest search, tagged with the query it answers: anything else means "still searching"
  const [result, setResult] = useState<{ for: string; items?: T[]; error?: string } | null>(null);
  const latest = useRef(load);
  useEffect(() => {
    latest.current = load; // always search with the newest loader without restarting the search
  });

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    const id = setTimeout(
      () => {
        latest
          .current(query.trim())
          .then((rows) => {
            if (!cancelled) setResult({ for: query, items: rows });
          })
          .catch((e: unknown) => {
            if (!cancelled) setResult({ for: query, error: toApiError(e).message });
          });
      },
      query === "" ? 0 : 250,
    );
    return () => {
      cancelled = true;
      clearTimeout(id);
    };
  }, [open, query]);

  const current = result?.for === query ? result : null;
  const items = current?.items ?? null;
  const error = current?.error ?? null;

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(next) => {
        if (!next) setQuery("");
        onOpenChange(next);
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-fg/40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 flex max-h-[85vh] w-[min(94vw,32rem)] -translate-x-1/2 -translate-y-1/2 flex-col gap-3 rounded-lg border border-border bg-surface-raised p-4 shadow-popover focus-visible:outline-none">
          <div>
            <Dialog.Title className="text-ui-md font-semibold text-fg">{title}</Dialog.Title>
            <Dialog.Description className="text-ui-sm text-fg-muted">{description}</Dialog.Description>
          </div>
          <TextInput type="search" aria-label={`Search: ${title}`} placeholder={placeholder} value={query} onChange={(e) => setQuery(e.target.value)} autoComplete="off" />
          <div className="min-h-24 flex-1 overflow-y-auto rounded-md border border-border">
            {error ? (
              <p role="alert" className="p-3 text-ui-sm text-danger">
                {error}
              </p>
            ) : items === null ? (
              <p role="status" className="p-3 text-ui-sm text-fg-muted">
                Searching...
              </p>
            ) : items.length === 0 ? (
              <p className="p-3 text-ui-sm text-fg-muted">{emptyMessage}</p>
            ) : (
              <ul>
                {items.map((item) => (
                  <li key={keyOf(item)} className="border-b border-border last:border-b-0">
                    <button
                      type="button"
                      onClick={() => {
                        onSelect(item);
                        setQuery("");
                        onOpenChange(false);
                      }}
                      className="block w-full px-3 py-2 text-left text-ui-base text-fg hover:bg-surface-hover focus-visible:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-line-focus"
                    >
                      {render(item)}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          {footer}
          <div className="flex justify-end">
            <Dialog.Close asChild>
              <Button>Close</Button>
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
