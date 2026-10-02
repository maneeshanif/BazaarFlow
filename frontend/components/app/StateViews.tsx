import type { ReactNode } from "react";
import { AlertTriangle, Inbox, Lock } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

/** The non-data states every data-bound view must have (ui-rules.md "States, all four, every time"). */

type Action = { label: string; onClick: () => void };

const actionClass =
  "inline-flex h-control-md items-center rounded-md border border-border bg-surface px-3 text-ui-base font-medium text-fg hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-focus";

function Frame({ icon, title, children, role }: { icon: ReactNode; title: string; children?: ReactNode; role?: "alert" }) {
  return (
    <div role={role} className="flex flex-col items-center gap-2 px-4 py-10 text-center">
      <span aria-hidden className="text-fg-subtle">
        {icon}
      </span>
      <p className="text-ui-md font-semibold text-fg">{title}</p>
      {children}
    </div>
  );
}

export function EmptyState({ message, action }: { message: string; action?: Action }) {
  return (
    <Frame icon={<Inbox className="h-6 w-6" />} title={message}>
      {action ? (
        <button type="button" className={actionClass} onClick={action.onClick}>
          {action.label}
        </button>
      ) : null}
    </Frame>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Frame role="alert" icon={<AlertTriangle className="h-6 w-6 text-danger" />} title={message}>
      {onRetry ? (
        <button type="button" className={actionClass} onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </Frame>
  );
}

export function UnauthorizedState({ message }: { message?: string }) {
  return (
    <Frame icon={<Lock className="h-6 w-6" />} title="Access is restricted">
      <p className="max-w-form text-ui-sm text-fg-muted">
        {message ?? "Your role does not include this page. Ask the shop owner if you need access."}
      </p>
    </Frame>
  );
}

/** Skeleton rows that match the table layout (not a centred spinner). */
export function TableSkeleton({ columns, rows = 5, className }: { columns: number; rows?: number; className?: string }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, r) => (
        <tr key={r} data-testid="skeleton-row" className={cn("border-t border-border", className)}>
          {Array.from({ length: columns }).map((__, c) => (
            <td key={c} className="px-3 py-2">
              <Skeleton className="h-4 w-full" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}
