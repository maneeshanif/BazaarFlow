"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { toast } from "sonner";
import { Button } from "@/components/app/Button";
import { DataTable, type Column } from "@/components/app/DataTable";
import { PageHeader } from "@/components/app/PageHeader";
import { ErrorState } from "@/components/app/StateViews";
import { Checkbox, SelectInput, TextArea, TextInput } from "@/components/form/Controls";
import { FormField } from "@/components/form/FormField";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useLoad } from "@/hooks/useLoad";
import { useSubmit } from "@/hooks/useSubmit";
import { apiGet, apiPut } from "@/lib/api/client";
import type { AssistantConfig, Page, VoiceCall, VoiceCallDetail, VoiceSettings } from "@/lib/api/types";
import { formatDateTime, formatNumber } from "@/lib/format";
import { fieldErrorsOf } from "@/lib/validation/common";
import { voiceSettingsSchema } from "@/lib/validation/voice";

type Values = {
  enabled: boolean;
  greeting: string;
  consent_notice: string;
  max_call_seconds: string;
  monthly_cap_usd: string;
  handoff_phone: string;
  retention_days: string;
};

const toValues = (s: VoiceSettings): Values => ({
  enabled: s.enabled,
  greeting: s.greeting,
  consent_notice: s.consent_notice,
  max_call_seconds: String(s.max_call_seconds),
  monthly_cap_usd: String(s.monthly_cap_usd),
  handoff_phone: s.handoff_phone ?? "",
  retention_days: String(s.retention_days),
});

function SettingsForm({ settings, canEdit, onSaved }: { settings: VoiceSettings; canEdit: boolean; onSaved: () => void }) {
  const [values, setValues] = useState<Values>(toValues(settings));
  const [submitted, setSubmitted] = useState(false);
  const save = useSubmit((body: unknown) => apiPut<VoiceSettings>("/voice/settings", body));
  const parsed = voiceSettingsSchema.safeParse(values);
  const live = parsed.success ? {} : fieldErrorsOf(parsed.error);
  const err = (n: string) => (submitted ? live[n] : undefined) ?? save.fieldErrors[n];
  const formLevel = save.error && Object.keys(save.fieldErrors).length === 0 ? save.error.message : undefined;
  const set = (key: keyof Values, value: string | boolean) => setValues((v) => ({ ...v, [key]: value }));

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitted(true);
    if (!parsed.success) return;
    if (await save.run({ ...parsed.data, handoff_phone: parsed.data.handoff_phone || null })) {
      toast.success("Saved your voice settings");
      onSaved();
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate aria-label="Voice settings" className="flex max-w-form flex-col gap-4 rounded-card border-2 border-line-strong bg-surface-raised p-6 shadow-card">
      {formLevel ? (
        <p role="alert" className="rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
          {formLevel}
        </p>
      ) : null}
      {!settings.vapi_connected ? (
        <p role="status" className="rounded-md border border-warning-border bg-warning-subtle px-3 py-2 text-ui-sm text-warning">
          VAPI is not connected, so the voice agent cannot be switched on.{" "}
          <Link href="/integrations" className="font-medium underline">
            Connect VAPI
          </Link>
        </p>
      ) : null}
      <label className="flex items-center gap-2 text-ui-base text-fg">
        <Checkbox checked={values.enabled} disabled={!canEdit} onChange={(e) => set("enabled", e.target.checked)} />
        Answer calls with the voice assistant
      </label>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <FormField id="voice-greeting" label="Greeting" required error={err("greeting")} className="md:col-span-2">
          <TextInput id="voice-greeting" value={values.greeting} disabled={!canEdit} onChange={(e) => set("greeting", e.target.value)} invalid={Boolean(err("greeting"))} />
        </FormField>
        <FormField id="voice-consent" label="Recording notice" required error={err("consent_notice")} hint="Spoken to every caller before anything else." className="md:col-span-2">
          <TextArea id="voice-consent" rows={2} value={values.consent_notice} disabled={!canEdit} onChange={(e) => set("consent_notice", e.target.value)} invalid={Boolean(err("consent_notice"))} />
        </FormField>
        <FormField id="voice-max" label="Longest call (seconds)" required error={err("max_call_seconds")} hint="60 to 900. The call is ended after this.">
          <TextInput id="voice-max" inputMode="numeric" value={values.max_call_seconds} disabled={!canEdit} onChange={(e) => set("max_call_seconds", e.target.value)} invalid={Boolean(err("max_call_seconds"))} />
        </FormField>
        <FormField
          id="voice-cap"
          label="Monthly voice budget (USD)"
          required
          error={err("monthly_cap_usd")}
          hint={`Spent this month: $${settings.month_spend_usd} (${settings.percent_used}%). New calls are refused once it is used up.`}
        >
          <TextInput id="voice-cap" inputMode="decimal" value={values.monthly_cap_usd} disabled={!canEdit} onChange={(e) => set("monthly_cap_usd", e.target.value)} invalid={Boolean(err("monthly_cap_usd"))} className="text-right font-mono tabular-nums" />
        </FormField>
        <FormField id="voice-phone" label="Phone for handoff" error={err("handoff_phone")} hint="Callers who ask for a person are passed here. Empty: they get a callback request.">
          <TextInput id="voice-phone" type="tel" value={values.handoff_phone} disabled={!canEdit} onChange={(e) => set("handoff_phone", e.target.value)} invalid={Boolean(err("handoff_phone"))} className="font-mono" />
        </FormField>
        <FormField id="voice-retention" label="Keep transcripts for (days)" required error={err("retention_days")} hint="After this the transcript and summary are deleted; the call record stays.">
          <TextInput id="voice-retention" inputMode="numeric" value={values.retention_days} disabled={!canEdit} onChange={(e) => set("retention_days", e.target.value)} invalid={Boolean(err("retention_days"))} />
        </FormField>
      </div>
      {canEdit ? (
        <div className="flex justify-end">
          <Button type="submit" variant="primary" loading={save.pending}>
            Save settings
          </Button>
        </div>
      ) : (
        <p className="text-ui-sm text-fg-muted">Only the owner can change these settings.</p>
      )}
    </form>
  );
}

function ConfigDialog({ onClose }: { onClose: () => void }) {
  const loaded = useLoad(() => apiGet<AssistantConfig>("/voice/assistant-config"), []);
  return (
    <Dialog.Root open onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-fg/40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[85vh] w-[min(94vw,44rem)] -translate-x-1/2 -translate-y-1/2 overflow-auto rounded-card border-2 border-line-strong bg-surface-raised-raised p-4 shadow-popover focus-visible:outline-none">
          <Dialog.Title className="text-ui-md font-semibold text-fg">Assistant to create in VAPI</Dialog.Title>
          <Dialog.Description className="text-ui-sm text-fg-muted">Copy this JSON into a new assistant in your VAPI dashboard, then follow the notes.</Dialog.Description>
          {loaded.state === "error" ? <p role="alert" className="mt-2 text-danger">{loaded.error?.message}</p> : null}
          {loaded.data ? (
            <>
              <ul className="mt-3 list-disc pl-5 text-ui-sm text-fg">
                {loaded.data.notes.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
              <pre className="mt-3 overflow-auto rounded-md bg-surface-sunken p-3 font-mono text-ui-xs text-fg">{JSON.stringify(loaded.data.assistant, null, 2)}</pre>
            </>
          ) : null}
          <div className="mt-3 flex justify-end">
            <Dialog.Close asChild>
              <Button>Close</Button>
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function CallDialog({ id, onClose }: { id: string; onClose: () => void }) {
  const loaded = useLoad(() => apiGet<VoiceCallDetail>(`/voice/calls/${id}`), [id]);
  const call = loaded.data;
  return (
    <Dialog.Root open onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-fg/40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[85vh] w-[min(94vw,40rem)] -translate-x-1/2 -translate-y-1/2 overflow-auto rounded-card border-2 border-line-strong bg-surface-raised-raised p-4 shadow-popover focus-visible:outline-none">
          <Dialog.Title className="text-ui-md font-semibold text-fg">Call details</Dialog.Title>
          <Dialog.Description className="text-ui-sm text-fg-muted">Personal details are removed from transcripts before they are stored.</Dialog.Description>
          {call ? (
            <div className="mt-3 flex flex-col gap-2 text-ui-sm">
              <p className="text-fg">
                {formatDateTime(call.started_at)} · {call.duration_seconds}s · ${call.cost_usd} · {call.turn_count} turns
                {call.avg_latency_ms !== null ? ` · average ${call.avg_latency_ms} ms a turn` : ""}
              </p>
              {call.handoff_note ? <p className="text-fg">Handed to a person: {call.handoff_note}</p> : null}
              {call.summary ? <p className="text-fg">{call.summary}</p> : null}
              {call.transcript ? <pre className="whitespace-pre-wrap rounded-md bg-surface-sunken p-3 font-mono text-ui-xs text-fg">{call.transcript}</pre> : null}
              {call.transcript_removed ? <p className="text-fg-muted">The transcript was deleted after your retention period.</p> : null}
            </div>
          ) : (
            <Skeleton className="mt-3 h-24 w-full" />
          )}
          <div className="mt-3 flex justify-end">
            <Dialog.Close asChild>
              <Button>Close</Button>
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

type Row = VoiceCall & { when: string; callerLabel: string; latency: string; open: string };

/** Voice calls and agent settings (PRD F-023). Owners edit; managers see. */
export function VoiceView() {
  const { role } = useAuth();
  const settings = useLoad(() => apiGet<VoiceSettings>("/voice/settings"), []);
  const [status, setStatus] = useState("");
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const [config, setConfig] = useState(false);
  const [opened, setOpened] = useState<string | null>(null);
  const cursor = cursors[cursors.length - 1] ?? null;
  const calls = useLoad(() => apiGet<Page<VoiceCall>>("/voice/calls", { status: status || undefined, limit: 25, cursor }), [status, cursor], (p) => p.items.length === 0);
  const rows: Row[] = (calls.data?.items ?? []).map((c) => ({
    ...c,
    when: formatDateTime(c.started_at),
    callerLabel: c.caller_hint ?? "Unknown",
    latency: c.avg_latency_ms === null ? "-" : `${c.avg_latency_ms} ms`,
    open: c.id,
  }));
  const columns: Column<Row>[] = [
    { key: "when", header: "When" },
    { key: "callerLabel", header: "Caller" },
    { key: "status", header: "Result", status: true },
    { key: "duration_seconds", header: "Seconds", numeric: true },
    { key: "latency", header: "Avg turn", numeric: true },
    { key: "cost_usd", header: "Cost (USD)", numeric: true },
    { key: "open", header: "", render: (r) => <Button size="sm" onClick={() => setOpened(r.id)}>Details</Button> },
  ];

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Voice"
        description="Your phone assistant: how it answers, what it costs, and the calls it took."
        actions={role === "owner" ? <Button onClick={() => setConfig(true)}>Assistant for VAPI</Button> : undefined}
      />
      {settings.state === "loading" ? <Skeleton className="h-48 max-w-form" /> : null}
      {settings.state === "error" ? <ErrorState message={settings.error?.message ?? "Could not load the voice settings."} onRetry={settings.reload} /> : null}
      {settings.data ? <SettingsForm key={`${settings.data.enabled}-${settings.data.percent_used}-${settings.data.configured}`} settings={settings.data} canEdit={role === "owner"} onSaved={settings.reload} /> : null}

      <section aria-label="Calls" className="flex flex-col gap-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 className="text-ui-md font-semibold text-fg">Calls</h2>
          <div className="flex flex-col gap-1">
            <label htmlFor="call-status" className="text-ui-xs font-medium text-fg-muted">
              Show
            </label>
            <SelectInput
              id="call-status"
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setCursors([null]);
              }}
            >
              <option value="">Every call</option>
              <option value="completed">Completed</option>
              <option value="escalated">Passed to a person</option>
              <option value="failed">Failed</option>
              <option value="in_progress">In progress</option>
            </SelectInput>
          </div>
        </div>
        <DataTable
          caption="Voice calls"
          columns={columns}
          rows={rows}
          state={calls.state}
          rowKey={(r) => r.id}
          emptyMessage={status ? "No calls with this result." : "No calls yet. Once VAPI is connected and the assistant is on, calls appear here."}
          errorMessage={calls.error?.message ?? "Could not load the calls."}
          onRetry={calls.reload}
        />
        {calls.state === "ready" ? (
          <nav aria-label="Pagination" className="flex items-center justify-between gap-2 text-ui-sm text-fg-muted">
            <span>{formatNumber(calls.data?.total ?? 0)} calls</span>
            <span className="flex gap-2">
              <Button size="sm" disabled={cursors.length === 1} onClick={() => setCursors((c) => c.slice(0, -1))}>
                Previous
              </Button>
              <Button size="sm" disabled={!calls.data?.next_cursor} onClick={() => calls.data?.next_cursor && setCursors((c) => [...c, calls.data?.next_cursor ?? null])}>
                Next
              </Button>
            </span>
          </nav>
        ) : null}
      </section>
      {config ? <ConfigDialog onClose={() => setConfig(false)} /> : null}
      {opened ? <CallDialog id={opened} onClose={() => setOpened(null)} /> : null}
    </div>
  );
}
