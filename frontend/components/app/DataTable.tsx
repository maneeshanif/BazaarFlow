"use client";

import type { ReactNode } from "react";
import { StatusBadge } from "@/components/app/StatusBadge";
import { EmptyState, ErrorState, TableSkeleton, UnauthorizedState } from "@/components/app/StateViews";
import { formatMoney } from "@/lib/format";
import { useT } from "@/lib/i18n/LocaleProvider";
import { cn } from "@/lib/utils";

export type Column<T> = {
  key: keyof T & string;
  header: string;
  /** right-aligned tabular figures */
  numeric?: boolean;
  /** formatted through lib/format, right-aligned */
  money?: boolean;
  mono?: boolean;
  /** rendered as a status badge */
  status?: boolean;
  render?: (row: T) => ReactNode;
};

type Props<T> = {
  caption: string;
  columns: Column<T>[];
  rows: T[];
  state: "ready" | "loading" | "empty" | "error" | "unauthorized";
  emptyMessage?: string;
  emptyAction?: { label: string; onClick: () => void };
  errorMessage?: string;
  onRetry?: () => void;
  rowKey?: (row: T, index: number) => string;
};

/**
 * The shared data grid (ui-rules.md "Data Grid"). Numbers and money are right-aligned, status is a text badge, the
 * header is sticky, and the grid scrolls horizontally inside its own container so the page body never does.
 */
export function DataTable<T extends Record<string, unknown>>({
  caption,
  columns,
  rows,
  state,
  emptyMessage = "Nothing here yet.",
  emptyAction,
  errorMessage = "Could not load this list.",
  onRetry,
  rowKey,
}: Props<T>) {
  const t = useT();
  const cellClass = (c: Column<T>) =>
    cn("px-4 py-3 text-ui-base text-fg", (c.numeric || c.money) && "text-end tabular-nums", c.money && "font-mono", c.mono && "font-mono");

  const message = (node: ReactNode) => (
    <tr>
      <td colSpan={columns.length} className="p-0">
        {node}
      </td>
    </tr>
  );

  return (
    <div data-testid="table-scroll" className="overflow-x-auto rounded-card border-2 border-line-strong bg-surface">
      <table className="w-max min-w-full border-collapse" aria-busy={state === "loading"}>
        <caption className="sr-only">{t(caption)}</caption>
        <thead>
          <tr className="sticky top-0 bg-lime text-forest-ink dark:bg-action-subtle dark:text-lime">
            {columns.map((c) => (
              <th
                key={c.key}
                scope="col"
                className={cn(
                  "px-4 py-3 text-start font-display text-ui-sm font-normal uppercase tracking-wide",
                  (c.numeric || c.money) && "text-end",
                )}
              >
                {t(c.header)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {state === "loading" && <TableSkeleton columns={columns.length} />}
          {state === "empty" && message(<EmptyState message={t(emptyMessage)} action={emptyAction ? { ...emptyAction, label: t(emptyAction.label) } : undefined} />)}
          {state === "error" && message(<ErrorState message={t(errorMessage)} onRetry={onRetry} />)}
          {state === "unauthorized" && message(<UnauthorizedState />)}
          {state === "ready" &&
            rows.map((row, i) => (
              <tr key={rowKey ? rowKey(row, i) : i} className="border-t-2 border-dotted border-line-strong hover:bg-surface-hover">
                {columns.map((c) => {
                  const value = row[c.key];
                  let content: ReactNode;
                  if (c.render) content = c.render(row);
                  else if (c.status) content = <StatusBadge status={String(value)} />;
                  else if (c.money) content = formatMoney(value as string | number | null);
                  else content = value === null || value === undefined ? "-" : String(value);
                  return c.status ? (
                    <td key={c.key} className={cellClass(c)}>
                      {content}
                    </td>
                  ) : (
                    <td key={c.key} className={cellClass(c)}>
                      {content}
                    </td>
                  );
                })}
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}
