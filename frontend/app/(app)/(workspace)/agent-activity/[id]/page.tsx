"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { buttonClass } from "@/components/app/Button";
import { PageHeader } from "@/components/app/PageHeader";
import { RequireRole } from "@/components/app/RequireRole";
import { ErrorState, UnauthorizedState } from "@/components/app/StateViews";
import { StatusBadge } from "@/components/app/StatusBadge";
import { Skeleton } from "@/components/ui/skeleton";
import { useLoad } from "@/hooks/useLoad";
import { apiGet } from "@/lib/api/client";
import type { AgentRunDetail } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

type Step = { tool: string; arguments: Record<string, unknown>; result: string; ok: boolean };

function Detail() {
  const { id } = useParams<{ id: string }>();
  const loaded = useLoad(() => apiGet<AgentRunDetail>(`/agent-runs/${id}`), [id]);

  if (loaded.state === "loading") {
    return (
      <div role="status" aria-busy="true" aria-label="Loading run" className="flex max-w-3xl flex-col gap-3">
        <Skeleton className="h-6 w-56" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }
  if (loaded.state === "unauthorized") return <UnauthorizedState />;
  if (loaded.state === "error" || !loaded.data) {
    const missing = loaded.error?.status === 404;
    return <ErrorState message={missing ? "That run does not exist." : (loaded.error?.message ?? "Could not load this run.")} onRetry={missing ? undefined : loaded.reload} />;
  }
  const run = loaded.data;
  const steps = run.trace as unknown as Step[];

  return (
    <div className="flex max-w-3xl flex-col gap-4">
      <PageHeader
        title="Agent run"
        description={`${formatDateTime(run.created_at)}${run.user_name ? `, asked by ${run.user_name}` : ""}`}
        actions={
          <Link href="/agent-activity" className={buttonClass("secondary")}>
            Back to activity
          </Link>
        }
      />
      <dl className="grid grid-cols-2 gap-3 rounded-lg border border-border bg-surface p-4 text-ui-sm md:grid-cols-4">
        <div>
          <dt className="text-ui-xs font-medium text-fg-muted">Result</dt>
          <dd className="mt-1">
            <StatusBadge status={run.outcome === "ok" ? "completed" : run.outcome} />
          </dd>
        </div>
        <div>
          <dt className="text-ui-xs font-medium text-fg-muted">Tokens (in / out)</dt>
          <dd className="mt-1 font-mono tabular-nums">
            {run.tokens_in} / {run.tokens_out}
          </dd>
        </div>
        <div>
          <dt className="text-ui-xs font-medium text-fg-muted">Cost</dt>
          <dd className="mt-1 font-mono tabular-nums">${run.spend_usd}</dd>
        </div>
        <div>
          <dt className="text-ui-xs font-medium text-fg-muted">Took</dt>
          <dd className="mt-1 font-mono tabular-nums">{run.duration_ms} ms</dd>
        </div>
      </dl>

      <section aria-label="The conversation" className="flex flex-col gap-2 rounded-lg border border-border bg-surface p-4">
        <h2 className="text-ui-md font-semibold text-fg">The conversation</h2>
        <p className="text-ui-sm">
          <span className="font-medium text-fg">They said: </span>
          <span className="whitespace-pre-line text-fg-muted">{run.input_text}</span>
        </p>
        <p className="text-ui-sm">
          <span className="font-medium text-fg">The assistant replied: </span>
          <span className="whitespace-pre-line text-fg-muted">{run.output_text}</span>
        </p>
        <p className="text-ui-xs text-fg-subtle">Names, phone numbers and emails are hidden in this record on purpose.</p>
      </section>

      <section aria-label="What the agent did" className="flex flex-col gap-2">
        <h2 className="text-ui-md font-semibold text-fg">What the agent did</h2>
        {steps.length === 0 ? (
          <p className="rounded-lg border border-border bg-surface p-4 text-ui-sm text-fg-muted">It answered without using any tools.</p>
        ) : (
          <ol className="flex flex-col gap-2">
            {steps.map((s, i) => (
              <li key={`${i}-${s.tool}`} className="rounded-lg border border-border bg-surface p-3 text-ui-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono font-medium text-fg">{s.tool}</span>
                  <StatusBadge status={s.ok ? "completed" : "failed"} />
                </div>
                <p className="mt-1 break-words font-mono text-ui-xs text-fg-muted">{JSON.stringify(s.arguments)}</p>
                <p className="mt-1 whitespace-pre-line text-fg">{s.result}</p>
              </li>
            ))}
          </ol>
        )}
        {run.action_ids.length > 0 ? (
          <p className="text-ui-sm text-fg-muted">
            It filed {run.action_ids.length} request{run.action_ids.length === 1 ? "" : "s"} for approval.{" "}
            <Link href="/approvals" className="font-medium text-action hover:underline">
              Open Approvals
            </Link>
          </p>
        ) : null}
      </section>
    </div>
  );
}

/** One agent run (PRD F-022): the redacted conversation and every tool it called. Owners and managers only. */
export default function AgentRunPage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <Detail />
    </RequireRole>
  );
}
