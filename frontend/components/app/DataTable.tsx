import type { ReactNode } from "react";
import { StatusBadge } from "@/components/app/StatusBadge";
import { EmptyState, ErrorState, TableSkeleton, UnauthorizedState } from "@/components/app/StateViews";
import { formatMoney } from "@/lib/format";
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
  const cellClass = (c: Column<T>) =>
    cn("px-3 py-2 text-ui-sm text-fg", (c.numeric || c.money) && "text-right tabular-nums", c.money && "font-mono", c.mono && "font-mono");

  const message = (node: ReactNode) => (
    <tr>
      <td colSpan={columns.length} className="p-0">
        {node}
      </td>
    </tr>
  );

  return (
    <div data-testid="table-scroll" className="overflow-x-auto rounded-lg border border-border bg-surface">
      <table className="w-max min-w-full border-collapse" aria-busy={state === "loading"}>
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr className="sticky top-0 bg-surface-sunken">
            {columns.map((c) => (
              <th
                key={c.key}
                scope="col"
                className={cn(
                  "px-3 py-2 text-left text-ui-xs font-medium text-fg-muted",
                  (c.numeric || c.money) && "text-right",
                )}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {state === "loading" && <TableSkeleton columns={columns.length} />}
          {state === "empty" && message(<EmptyState message={emptyMessage} action={emptyAction} />)}
          {state === "error" && message(<ErrorState message={errorMessage} onRetry={onRetry} />)}
          {state === "unauthorized" && message(<UnauthorizedState />)}
          {state === "ready" &&
            rows.map((row, i) => (
              <tr key={rowKey ? rowKey(row, i) : i} className="border-t border-border hover:bg-surface-hover">
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
