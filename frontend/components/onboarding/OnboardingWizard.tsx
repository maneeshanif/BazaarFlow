"use client";

import Link from "next/link";
import { useState, type ChangeEvent, type FormEvent } from "react";
import { toast } from "sonner";
import { Button, buttonClass } from "@/components/app/Button";
import { PageHeader } from "@/components/app/PageHeader";
import { ErrorState } from "@/components/app/StateViews";
import { StatusBadge } from "@/components/app/StatusBadge";
import { TextArea, TextInput } from "@/components/form/Controls";
import { FormField } from "@/components/form/FormField";
import { Skeleton } from "@/components/ui/skeleton";
import { useLoad } from "@/hooks/useLoad";
import { useSubmit } from "@/hooks/useSubmit";
import { apiGet, apiPost, apiPut } from "@/lib/api/client";
import type { ImportReport, Onboarding, TestMessageResult } from "@/lib/api/types";
import { fieldErrorsOf } from "@/lib/validation/common";
import { onboardingShopSchema } from "@/lib/validation/channels";

const SAMPLE = "sku,name,price,cost,qty,category\nSH-1,Classic Shirt,2500,1800,10,Clothes\nCAP-1,Cap,500,,5,";

function ShopStep({ state, onDone }: { state: Onboarding; onDone: () => void }) {
  const [values, setValues] = useState({ name: state.shop_name, owner_phone: state.owner_phone ?? "+92", city: "" });
  const [submitted, setSubmitted] = useState(false);
  const save = useSubmit((body: unknown) => apiPut<Onboarding>("/onboarding/shop", body));
  const parsed = onboardingShopSchema.safeParse(values);
  const live = parsed.success ? {} : fieldErrorsOf(parsed.error);
  const err = (n: string) => (submitted ? live[n] : undefined) ?? save.fieldErrors[n];
  const formLevel = save.error && Object.keys(save.fieldErrors).length === 0 ? save.error.message : undefined;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitted(true);
    if (!parsed.success) return;
    if (await save.run({ ...parsed.data, city: parsed.data.city || null })) onDone();
  }

  return (
    <form onSubmit={onSubmit} noValidate aria-label="Shop details" className="flex flex-col gap-4">
      {formLevel ? (
        <p role="alert" className="rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
          {formLevel}
        </p>
      ) : null}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <FormField id="ob-name" label="Shop name" required error={err("name")}>
          <TextInput id="ob-name" value={values.name} onChange={(e) => setValues((v) => ({ ...v, name: e.target.value }))} invalid={Boolean(err("name"))} />
        </FormField>
        <FormField id="ob-phone" label="Your phone" required error={err("owner_phone")} hint="For your daily briefing and the test message.">
          <TextInput id="ob-phone" type="tel" value={values.owner_phone} onChange={(e) => setValues((v) => ({ ...v, owner_phone: e.target.value }))} invalid={Boolean(err("owner_phone"))} className="font-mono" />
        </FormField>
        <FormField id="ob-city" label="City" error={err("city")}>
          <TextInput id="ob-city" value={values.city} onChange={(e) => setValues((v) => ({ ...v, city: e.target.value }))} invalid={Boolean(err("city"))} />
        </FormField>
      </div>
      <div className="flex justify-end">
        <Button type="submit" variant="primary" loading={save.pending}>
          Save and continue
        </Button>
      </div>
    </form>
  );
}

function ChannelsStep({ state, onDone }: { state: Onboarding; onDone: () => void }) {
  const next = useSubmit(() => apiPost<Onboarding>("/onboarding/channels/continue"));
  return (
    <div className="flex flex-col gap-3">
      <p className="text-ui-base text-fg">Customers message you on WhatsApp and your posts go to Facebook. You can connect either now or skip and do it later.</p>
      <ul className="flex flex-col gap-1 text-ui-sm">
        <li className="flex items-center gap-2">
          WhatsApp <StatusBadge status={state.whatsapp_connected ? "connected" : "disabled"} label={state.whatsapp_connected ? "connected" : "not connected"} />
        </li>
        <li className="flex items-center gap-2">
          Facebook <StatusBadge status={state.facebook_connected ? "connected" : "disabled"} label={state.facebook_connected ? "connected" : "not connected"} />
        </li>
      </ul>
      <p className="text-ui-sm text-fg-muted">
        <Link href="/integrations" className="font-medium text-action hover:underline" target="_blank">
          Open integrations in a new tab
        </Link>
        , connect them, then come back here and continue.
      </p>
      <div className="flex justify-end gap-2">
        <Button variant="primary" loading={next.pending} onClick={async () => (await next.run()) && onDone()}>
          {state.whatsapp_connected || state.facebook_connected ? "Continue" : "Skip for now"}
        </Button>
      </div>
      {next.error ? (
        <p role="alert" className="text-ui-sm text-danger">
          {next.error.message}
        </p>
      ) : null}
    </div>
  );
}

function ProductsStep({ state, onDone }: { state: Onboarding; onDone: () => void }) {
  const [csv, setCsv] = useState("");
  const [report, setReport] = useState<ImportReport | null>(null);
  const importer = useSubmit((text: string) => apiPost<ImportReport>("/onboarding/products/import", { csv: text }));
  const next = useSubmit(() => apiPost<Onboarding>("/onboarding/products/continue"));

  async function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) setCsv(await file.text());
  }
  async function onImport() {
    const done = await importer.run(csv);
    if (done) {
      setReport(done);
      toast.success(`Imported ${done.imported} ${done.imported === 1 ? "product" : "products"}`);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-ui-base text-fg">
        You have {state.product_count} {state.product_count === 1 ? "product" : "products"}. Paste or upload a CSV with the columns <span className="font-mono">sku, name, price</span> (and optionally cost, qty, category), or{" "}
        <Link href="/inventory/new" className="font-medium text-action hover:underline" target="_blank">
          add one by hand
        </Link>
        .
      </p>
      <FormField id="ob-file" label="CSV file">
        <input id="ob-file" type="file" accept=".csv,text/csv" onChange={(e) => void onFile(e)} className="text-ui-sm text-fg" />
      </FormField>
      <FormField id="ob-csv" label="Or paste it here" hint="The first line is the header. Good rows are imported; bad rows are listed.">
        <TextArea id="ob-csv" rows={6} value={csv} onChange={(e) => setCsv(e.target.value)} placeholder={SAMPLE} className="font-mono" />
      </FormField>
      {importer.error ? (
        <p role="alert" className="text-ui-sm text-danger">
          {importer.error.message}
        </p>
      ) : null}
      {report ? (
        <div role="status" className="rounded-md border border-border bg-surface px-3 py-2 text-ui-sm">
          <p className="font-medium text-fg">
            Imported {report.imported}; {report.failed.length} could not be imported.
          </p>
          {report.failed.length > 0 ? (
            <ul className="mt-1 list-disc pl-4 text-fg-muted">
              {report.failed.map((f) => (
                <li key={f.row}>
                  Line {f.row}
                  {f.sku ? ` (${f.sku})` : ""}: {f.error}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
      <div className="flex flex-wrap justify-end gap-2">
        <Button onClick={() => void onImport()} loading={importer.pending} disabled={csv.trim() === ""}>
          Import products
        </Button>
        <Button variant="primary" loading={next.pending} onClick={async () => (await next.run()) && onDone()}>
          {state.product_count > 0 || (report?.imported ?? 0) > 0 ? "Continue" : "Skip for now"}
        </Button>
      </div>
    </div>
  );
}

function TestStep({ state, onDone }: { state: Onboarding; onDone: () => void }) {
  const [result, setResult] = useState<TestMessageResult | null>(null);
  const test = useSubmit(() => apiPost<TestMessageResult>("/onboarding/test-message"));
  const finish = useSubmit(() => apiPost<Onboarding>("/onboarding/finish"));
  return (
    <div className="flex flex-col gap-3">
      <p className="text-ui-base text-fg">
        Send yourself a WhatsApp message to check everything works{state.owner_phone ? ` (it goes to ${state.owner_phone})` : ""}. You can skip this and go live.
      </p>
      {result ? (
        <p role={result.sent ? "status" : "alert"} className={result.sent ? "text-ui-sm text-success" : "text-ui-sm text-danger"}>
          {result.detail}
        </p>
      ) : null}
      <div className="flex flex-wrap justify-end gap-2">
        <Button
          loading={test.pending}
          onClick={async () => {
            const done = await test.run();
            if (!done) return;
            setResult(done);
            if (done.sent) onDone();
          }}
        >
          Send a test message
        </Button>
        <Button variant="primary" loading={finish.pending} onClick={async () => (await finish.run()) && onDone()}>
          Go live without a test
        </Button>
      </div>
    </div>
  );
}

/** The onboarding wizard (PRD F-003): shop details, channels, products, a test message. Owners only. */
export function OnboardingWizard() {
  const loaded = useLoad(() => apiGet<Onboarding>("/onboarding/"), []);
  const state = loaded.data;
  if (loaded.state === "loading" && !state) return <Skeleton className="h-64 max-w-form" />;
  if (loaded.state === "error" || !state) return <ErrorState message={loaded.error?.message ?? "Could not load the setup guide."} onRetry={loaded.reload} />;
  const current = state.steps.find((s) => s.status === "current")?.key;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Set up your shop" description="Four short steps. Only the shop details are required." />
      <ol aria-label="Steps" className="flex flex-wrap gap-2">
        {state.steps.map((s, i) => (
          <li key={s.key} aria-current={s.status === "current" ? "step" : undefined} className="flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-1 text-ui-sm">
            <span className="text-fg-muted">{i + 1}.</span>
            <span className="text-fg">{s.label}</span>
            <StatusBadge status={s.status === "done" ? "completed" : s.status === "current" ? "in_progress" : "disabled"} label={s.status} />
          </li>
        ))}
      </ol>
      <section aria-label="Current step" className="max-w-form rounded-lg border border-border bg-surface p-4">
        {state.state === "live" || !current ? (
          <div className="flex flex-col items-start gap-3">
            <h2 className="text-ui-md font-semibold text-fg">Your shop is live</h2>
            <p className="text-ui-sm text-fg-muted">Everything is set up. You can change any of it later in Settings.</p>
            <Link href="/dashboard" className={buttonClass("primary")}>
              Go to your home screen
            </Link>
          </div>
        ) : (
          <>
            <h2 className="mb-3 text-ui-md font-semibold text-fg">{state.steps.find((s) => s.key === current)?.label}</h2>
            {current === "shop" ? <ShopStep state={state} onDone={loaded.reload} /> : null}
            {current === "channels" ? <ChannelsStep state={state} onDone={loaded.reload} /> : null}
            {current === "products" ? <ProductsStep state={state} onDone={loaded.reload} /> : null}
            {current === "test" ? <TestStep state={state} onDone={loaded.reload} /> : null}
          </>
        )}
      </section>
    </div>
  );
}
