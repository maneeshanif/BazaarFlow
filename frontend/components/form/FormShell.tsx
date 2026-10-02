import type { ReactNode } from "react";
import { StatusBadge } from "@/components/app/StatusBadge";
import { cn } from "@/lib/utils";

type Props = {
  title: string;
  /** document / posting state shown as a badge in the header */
  status?: string;
  /** "transaction" has a detail grid and totals; "master" is fields only (company, branch, settings) */
  mode?: "transaction" | "master";
  /** filters or master fields */
  filters?: ReactNode;
  /** the detail grid (transaction) or the master fields (master mode) */
  children?: ReactNode;
  totals?: ReactNode;
  actions: ReactNode;
  /** audit / status panel: who created and changed this, last agent action */
  audit?: ReactNode;
};

const panel = "rounded-lg border border-border bg-surface p-4";

/**
 * The mandated form layout (PRD §5.1, ui-rules.md): header -> filters or master fields -> detail grid -> totals ->
 * actions -> audit panel. Every form composes this component; nobody hand-rolls the order.
 */
export function FormShell({ title, status, mode = "transaction", filters, children, totals, actions, audit }: Props) {
  const master = mode === "master";
  return (
    <section aria-label={title} className={cn("flex flex-col gap-4", master && "max-w-form")}>
      <header data-testid="form-header" className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-ui-lg font-semibold text-fg">{title}</h1>
        {status ? <StatusBadge status={status} /> : null}
      </header>

      <div data-testid="form-filters" className={panel}>
        {master ? children : filters}
      </div>

      {!master && (
        <div data-testid="form-grid" className="min-w-0">
          {children}
        </div>
      )}

      {!master && totals ? (
        <div data-testid="form-totals" className={panel}>
          {totals}
        </div>
      ) : null}

      <div data-testid="form-actions" className="flex flex-wrap items-center justify-end gap-2">
        {actions}
      </div>

      {audit ? (
        <aside data-testid="form-audit" aria-label="Audit and status" className={cn(panel, "text-ui-xs text-fg-muted")}>
          {audit}
        </aside>
      ) : null}
    </section>
  );
}
