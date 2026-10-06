"use client";

import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Button } from "@/components/app/Button";
import { ConfirmDialog } from "@/components/app/ConfirmDialog";
import { PageHeader } from "@/components/app/PageHeader";
import { ErrorState } from "@/components/app/StateViews";
import { StatusBadge } from "@/components/app/StatusBadge";
import { TextInput } from "@/components/form/Controls";
import { FormField } from "@/components/form/FormField";
import { Skeleton } from "@/components/ui/skeleton";
import { useLoad } from "@/hooks/useLoad";
import { useSubmit } from "@/hooks/useSubmit";
import { apiDelete, apiGet, apiPut } from "@/lib/api/client";
import type { Integration } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { fieldErrorsOf } from "@/lib/validation/common";
import { facebookSchema, twilioSchema, vapiSchema } from "@/lib/validation/channels";

type FieldDef = { name: string; label: string; hint: string; secret?: boolean; mono?: boolean };

const FIELDS: Record<string, FieldDef[]> = {
  whatsapp_twilio: [
    { name: "account_sid", label: "Account SID", hint: "From your Twilio console. It starts with AC.", mono: true },
    { name: "auth_token", label: "Auth Token", hint: "From your Twilio console. It is saved encrypted and never shown again.", secret: true, mono: true },
  ],
  vapi: [
    { name: "assistant_id", label: "Assistant id", hint: "From your VAPI dashboard.", mono: true },
    { name: "webhook_secret", label: "Webhook token", hint: "The Bearer token you set for the server URL in VAPI. Saved encrypted and never shown again.", secret: true, mono: true },
  ],
  facebook: [
    { name: "page_id", label: "Page id", hint: "The number in your page's About section.", mono: true },
    { name: "access_token", label: "Page access token", hint: "A long-lived Page token. It is saved encrypted and never shown again.", secret: true, mono: true },
  ],
};

function ConnectForm({ integration, onDone }: { integration: Integration; onDone: () => void }) {
  const fields = FIELDS[integration.provider] ?? [];
  const schema = integration.provider === "whatsapp_twilio" ? twilioSchema : integration.provider === "vapi" ? vapiSchema : facebookSchema;
  const [values, setValues] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState(false);
  const save = useSubmit((credentials: Record<string, string>) => apiPut<Integration>(`/integrations/${integration.provider}`, { credentials }));

  const parsed = schema.safeParse(values);
  const live = parsed.success ? {} : fieldErrorsOf(parsed.error);
  const err = (name: string) => (submitted ? live[name] : undefined) ?? save.fieldErrors[name];
  const formLevel = save.error && Object.keys(save.fieldErrors).length === 0 ? save.error.message : undefined;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitted(true);
    if (!parsed.success) return;
    const done = await save.run(parsed.data as Record<string, string>);
    if (!done) return;
    toast.success(`${integration.label} connected`);
    setValues({});
    onDone();
  }

  return (
    <form onSubmit={onSubmit} noValidate aria-label={`Connect ${integration.label}`} className="mt-3 flex flex-col gap-3">
      {formLevel ? (
        <p role="alert" className="rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
          {formLevel}
        </p>
      ) : null}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {fields.map((f) => (
          <FormField key={f.name} id={`${integration.provider}-${f.name}`} label={f.label} required error={err(f.name)} hint={f.hint}>
            <TextInput
              id={`${integration.provider}-${f.name}`}
              type={f.secret ? "password" : "text"}
              autoComplete="off"
              value={values[f.name] ?? ""}
              onChange={(e) => setValues((v) => ({ ...v, [f.name]: e.target.value }))}
              invalid={Boolean(err(f.name))}
              className={f.mono ? "font-mono" : undefined}
            />
          </FormField>
        ))}
      </div>
      <div className="flex justify-end">
        <Button type="submit" variant="primary" loading={save.pending}>
          {integration.reconnect_required ? "Reconnect" : "Connect"}
        </Button>
      </div>
    </form>
  );
}

function Card({ integration, onChanged }: { integration: Integration; onChanged: () => void }) {
  const [editing, setEditing] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const remove = useSubmit(async () => {
    await apiDelete(`/integrations/${integration.provider}`);
    return true;
  });
  const connected = integration.status === "connected";
  const canConnect = integration.available && !connected;

  async function onDisconnect() {
    if (!(await remove.run())) return;
    toast.success(`${integration.label} disconnected`);
    setConfirm(false);
    onChanged();
  }

  return (
    <li className="rounded-lg border border-border bg-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <h2 className="text-ui-md font-semibold text-fg">{integration.label}</h2>
          {integration.external_id ? <p className="font-mono text-ui-xs text-fg-muted">{integration.external_id}</p> : null}
        </div>
        {integration.available ? (
          <StatusBadge status={integration.status === "not_connected" ? "disabled" : integration.status} label={integration.status.replace("_", " ")} />
        ) : (
          <StatusBadge status="disabled" label="coming soon" />
        )}
      </div>

      {integration.reconnect_required ? (
        <p role="alert" className="mt-3 rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
          {integration.last_error ?? "This connection needs to be set up again."} Posts and messages are paused until you reconnect.
        </p>
      ) : integration.last_error ? (
        <p role="status" className="mt-3 rounded-md border border-warning-border bg-warning-subtle px-3 py-2 text-ui-sm text-warning">
          {integration.last_error}
        </p>
      ) : null}

      {connected ? (
        <dl className="mt-3 grid grid-cols-2 gap-2 text-ui-sm">
          <div>
            <dt className="text-fg-muted">Saved token</dt>
            <dd className="font-mono text-fg">{integration.token_hint ?? "-"}</dd>
          </div>
          <div>
            <dt className="text-fg-muted">Connected</dt>
            <dd className="text-fg">{integration.connected_at ? formatDateTime(integration.connected_at) : "-"}</dd>
          </div>
        </dl>
      ) : null}

      {integration.provider === "vapi" ? (
        <p className="mt-3 text-ui-sm text-fg-muted">
          In VAPI the server URL is <span className="break-all font-mono text-fg">your API address + /api/v1/webhooks/vapi</span>. The Voice page shows the exact assistant to create.
        </p>
      ) : null}
      {integration.webhook_url ? (
        <p className="mt-3 text-ui-sm text-fg-muted">
          In Twilio, set &quot;When a message comes in&quot; (POST) to <span className="break-all font-mono text-fg">{integration.webhook_url}</span>
        </p>
      ) : null}

      {!integration.available ? <p className="mt-3 text-ui-sm text-fg-muted">This channel is not available yet.</p> : null}

      <div className="mt-3 flex flex-wrap gap-2">
        {canConnect && !editing ? (
          <Button variant="primary" onClick={() => setEditing(true)}>
            {integration.reconnect_required ? "Reconnect" : "Connect"}
          </Button>
        ) : null}
        {connected ? (
          <Button variant="danger" onClick={() => setConfirm(true)}>
            Disconnect
          </Button>
        ) : null}
      </div>
      {editing && canConnect ? (
        <ConnectForm
          integration={integration}
          onDone={() => {
            setEditing(false);
            onChanged();
          }}
        />
      ) : null}

      <ConfirmDialog
        open={confirm}
        onOpenChange={setConfirm}
        title={`Disconnect ${integration.label}?`}
        confirmLabel="Disconnect"
        pending={remove.pending}
        onConfirm={() => void onDisconnect()}
      >
        <p>The saved token is deleted. Messages stop arriving and scheduled posts pause until you connect again.</p>
        {remove.error ? (
          <p role="alert" className="mt-2 text-danger">
            {remove.error.message}
          </p>
        ) : null}
      </ConfirmDialog>
    </li>
  );
}

/** Connect WhatsApp and Facebook (PRD F-018). Owners only; credentials go in and never come out. */
export function IntegrationsView() {
  const loaded = useLoad(() => apiGet<Integration[]>("/integrations/"), []);
  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Integrations" description="Connect your WhatsApp and Facebook so customers can reach you and your posts go out." />
      {loaded.state === "loading" ? (
        <div role="status" aria-busy="true" aria-label="Loading integrations" className="flex flex-col gap-3">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
        </div>
      ) : null}
      {loaded.state === "error" ? <ErrorState message={loaded.error?.message ?? "Could not load your integrations."} onRetry={loaded.reload} /> : null}
      {loaded.data ? (
        <ul className="flex max-w-form flex-col gap-3">
          {loaded.data.map((i) => (
            <Card key={`${i.provider}-${i.status}`} integration={i} onChanged={loaded.reload} />
          ))}
        </ul>
      ) : null}
    </div>
  );
}
