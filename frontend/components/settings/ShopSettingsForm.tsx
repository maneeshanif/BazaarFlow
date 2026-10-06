"use client";

import { useMemo, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Button } from "@/components/app/Button";
import { TextInput } from "@/components/form/Controls";
import { FormField } from "@/components/form/FormField";
import { FormShell } from "@/components/form/FormShell";
import { useSubmit } from "@/hooks/useSubmit";
import { apiPatch } from "@/lib/api/client";
import type { ShopSettings } from "@/lib/api/types";
import { formatDateTime, formatMoney } from "@/lib/format";
import { fieldErrorsOf } from "@/lib/validation/common";
import { shopSettingsSchema } from "@/lib/validation/shop";

type Values = { name: string; owner_phone: string; city: string; auto_post_limit: string };

const toValues = (s: ShopSettings): Values => ({
  name: s.name,
  owner_phone: s.owner_phone ?? "+92",
  city: s.city ?? "",
  auto_post_limit: s.auto_post_limit ?? "",
});

/** The owner's shop profile and settings (PRD F-020) in the mandated master-form layout. */
export function ShopSettingsForm({ shop, onSaved }: { shop: ShopSettings; onSaved: (s: ShopSettings) => void }) {
  const [values, setValues] = useState<Values>(toValues(shop));
  const [touched, setTouched] = useState<ReadonlySet<string>>(new Set());
  const [submitted, setSubmitted] = useState(false);

  const save = useSubmit(async (v: Values) => {
    const parsedBody = shopSettingsSchema.parse(v);
    return apiPatch<ShopSettings>("/settings/shop", {
      name: parsedBody.name,
      owner_phone: parsedBody.owner_phone,
      city: parsedBody.city,
      auto_post_limit: parsedBody.auto_post_limit === "" ? null : parsedBody.auto_post_limit,
    });
  });

  const parsed = useMemo(() => shopSettingsSchema.safeParse(values), [values]);
  const liveErrors = parsed.success ? {} : fieldErrorsOf(parsed.error);
  const err = (field: string): string | undefined => (touched.has(field) || submitted ? liveErrors[field] : undefined) ?? save.fieldErrors[field];
  const touch = (field: string) => setTouched((prev) => new Set(prev).add(field));
  const set = <K extends keyof Values>(key: K, value: string) => setValues((v) => ({ ...v, [key]: value }));
  const formLevel = save.error && Object.keys(save.fieldErrors).length === 0 ? save.error.message : undefined;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitted(true);
    if (!parsed.success) return;
    const saved = await save.run(values);
    if (!saved) return;
    toast.success("Saved your shop settings");
    setValues(toValues(saved));
    setSubmitted(false);
    onSaved(saved);
  }

  return (
    <form onSubmit={onSubmit} noValidate aria-label="Shop profile">
      <FormShell
        mode="master"
        title="Shop profile"
        actions={
          <Button type="submit" variant="primary" loading={save.pending}>
            Save changes
          </Button>
        }
        audit={
          <p>
            Created {formatDateTime(shop.created_at)}. Last changed {formatDateTime(shop.updated_at)}. Every change is recorded in the audit log.
          </p>
        }
      >
        {formLevel ? (
          <p role="alert" className="mb-4 rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
            {formLevel}
          </p>
        ) : null}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <FormField id="shop-name" label="Shop name" required error={err("name")}>
            <TextInput id="shop-name" autoComplete="organization" value={values.name} onChange={(e) => set("name", e.target.value)} onBlur={() => touch("name")} invalid={Boolean(err("name"))} />
          </FormField>
          <FormField id="shop-phone" label="Your phone" required error={err("owner_phone")} hint="Used for your daily briefing and alerts.">
            <TextInput id="shop-phone" type="tel" inputMode="tel" value={values.owner_phone} onChange={(e) => set("owner_phone", e.target.value)} onBlur={() => touch("owner_phone")} invalid={Boolean(err("owner_phone"))} className="font-mono" />
          </FormField>
          <FormField id="shop-city" label="City" error={err("city")}>
            <TextInput id="shop-city" autoComplete="address-level2" value={values.city} onChange={(e) => set("city", e.target.value)} onBlur={() => touch("city")} invalid={Boolean(err("city"))} />
          </FormField>
          <FormField
            id="shop-auto-post"
            label="Let the AI post sales up to (Rs)"
            error={err("auto_post_limit")}
            hint={`Empty means the AI always asks you first. Today it asks unless a sale is ${formatMoney(shop.effective_auto_post_limit)} or less.`}
          >
            <TextInput id="shop-auto-post" inputMode="decimal" value={values.auto_post_limit} onChange={(e) => set("auto_post_limit", e.target.value)} onBlur={() => touch("auto_post_limit")} invalid={Boolean(err("auto_post_limit"))} className="text-right font-mono tabular-nums" />
          </FormField>
        </div>
        <dl className="mt-6 grid grid-cols-2 gap-x-4 gap-y-2 text-ui-sm md:grid-cols-4">
          <div>
            <dt className="text-fg-muted">Plan</dt>
            <dd className="font-medium text-fg">{shop.plan}</dd>
          </div>
          <div>
            <dt className="text-fg-muted">Currency</dt>
            <dd className="font-medium text-fg">{shop.currency}</dd>
          </div>
          <div>
            <dt className="text-fg-muted">Time zone</dt>
            <dd className="font-medium text-fg">{shop.timezone}</dd>
          </div>
          <div>
            <dt className="text-fg-muted">AI assistant</dt>
            <dd className="font-medium text-fg">{shop.agents_enabled ? "On" : "Off"}</dd>
          </div>
        </dl>
      </FormShell>
    </form>
  );
}
