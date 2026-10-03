"use client";

import { toast } from "sonner";
import { Button } from "@/components/app/Button";
import { StatusBadge } from "@/components/app/StatusBadge";
import { useSubmit } from "@/hooks/useSubmit";
import { apiPut } from "@/lib/api/client";
import type { AgentStatus } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { cn } from "@/lib/utils";

/** The shop's AI switch and monthly allowance. Only the owner flips the switch; it takes effect on the next message. */
export function AgentStatusPanel({ status, onChanged }: { status: AgentStatus; onChanged: (s: AgentStatus) => void }) {
  const { role } = useAuth();
  const flip = useSubmit((enabled: boolean) => apiPut<AgentStatus>("/agent-runs/switch", { enabled }));
  const nearLimit = status.percent_used >= 80;

  async function onFlip() {
    const next = await flip.run(!status.enabled);
    if (!next) return;
    onChanged(next);
    toast.success(next.enabled ? "The AI assistant is on." : "The AI assistant is paused. It will not run until you switch it back on.");
  }

  return (
    <section aria-label="AI assistant status" className="grid gap-4 rounded-lg border border-border bg-surface p-4 md:grid-cols-[1fr_1fr_auto] md:items-center">
      <div>
        <h2 className="text-ui-md font-semibold text-fg">AI assistant</h2>
        <p className="mt-1 flex items-center gap-2 text-ui-sm text-fg-muted">
          <StatusBadge status={status.enabled ? "active" : "paused"} />
          {status.enabled ? "Answering your team's messages." : "Paused. Nobody can use it until it is switched on."}
        </p>
      </div>
      <div>
        <p className="text-ui-xs font-medium text-fg-muted">Allowance this month</p>
        <p className="mt-1 font-mono text-ui-base tabular-nums text-fg">
          ${status.month_spend_usd} of ${status.month_cap_usd} used ({status.percent_used}%)
        </p>
        <div
          role="progressbar"
          aria-label="AI allowance used this month"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.min(status.percent_used, 100)}
          className="mt-2 h-2 w-full overflow-hidden rounded-sm bg-surface-sunken"
        >
          <div className={cn("h-full", nearLimit ? "bg-warning" : "bg-action")} style={{ width: `${Math.min(status.percent_used, 100)}%` }} />
        </div>
        {nearLimit ? <p className="mt-1 text-ui-xs text-warning">{status.percent_used >= 100 ? "The allowance is used up; the assistant is stopped until next month." : "More than 80% of the allowance is used."}</p> : null}
      </div>
      {role === "owner" ? (
        <div className="flex flex-col items-end gap-1">
          <Button variant={status.enabled ? "secondary" : "primary"} loading={flip.pending} onClick={() => void onFlip()}>
            {status.enabled ? "Pause the assistant" : "Switch it on"}
          </Button>
          {flip.error ? (
            <p role="alert" className="text-ui-xs text-danger">
              {flip.error.message}
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
