import type { ReactNode } from "react";
import { AlertTriangle, Inbox, Lock } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

/** The non-data states every data-bound view must have (ui-rules.md "States, all four, every time"). */

type Action = { label: string; onClick: () => void };

const actionClass =
  "inline-flex h-control-md items-center rounded-pill border-2 border-action bg-surface px-5 text-ui-base font-bold text-fg hover:bg-lime hover:text-forest-ink focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-line-focus";

function Frame({ icon, title, children, role }: { icon: ReactNode; title: string; children?: ReactNode; role?: "alert" }) {
  return (
    <div role={role} className="flex flex-col items-center gap-2 px-4 py-10 text-center">
      <span aria-hidden className="flex h-16 w-16 items-center justify-center rounded-full bg-lime text-forest-ink">
        {icon}
      </span>
      <p className="font-display text-ui-xl uppercase text-fg">{title}</p>
      {children}
    </div>
  );
}

export function EmptyState({ message, action }: { message: string; action?: Action }) {
  return (
    <Frame icon={<Inbox className="h-7 w-7" />} title={message}>
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
    <Frame role="alert" icon={<AlertTriangle className="h-7 w-7" />} title={message}>
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
    <Frame icon={<Lock className="h-7 w-7" />} title="Access is restricted">
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
            <td key={c} className="px-4 py-3">
              <Skeleton className="h-5 w-full" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}
