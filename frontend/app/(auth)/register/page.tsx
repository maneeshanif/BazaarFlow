"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState, type FormEvent } from "react";
import { Button } from "@/components/app/Button";
import { Checkbox, TextInput } from "@/components/form/Controls";
import { FormField } from "@/components/form/FormField";
import { useSubmit } from "@/hooks/useSubmit";
import { useAuth, type RegisterResult } from "@/lib/auth/AuthProvider";
import { fieldErrorsOf } from "@/lib/validation/common";
import { normalizePhone, registerSchema } from "@/lib/validation/register";

type Values = {
  full_name: string;
  email: string;
  password: string;
  shop_name: string;
  phone: string;
  city: string;
  accept_terms: boolean;
};

const empty: Values = { full_name: "", email: "", password: "", shop_name: "", phone: "+92", city: "", accept_terms: false };

/** Create account and shop (PRD F-002): one step, then straight into the shop. */
export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [values, setValues] = useState<Values>(empty);
  const [touched, setTouched] = useState<ReadonlySet<string>>(new Set());
  const [submitted, setSubmitted] = useState(false);
  const [serverFields, setServerFields] = useState<Record<string, string>>({});
  const [banner, setBanner] = useState<string | null>(null);

  const attempt = useSubmit(
    (): Promise<RegisterResult> =>
      register({
        full_name: values.full_name.trim(),
        email: values.email.trim(),
        password: values.password,
        shop_name: values.shop_name.trim(),
        phone: normalizePhone(values.phone),
        ...(values.city.trim() ? { city: values.city.trim() } : {}),
        accept_terms: values.accept_terms,
      }),
  );

  const parsed = useMemo(() => registerSchema.safeParse(values), [values]);
  const liveErrors = parsed.success ? {} : fieldErrorsOf(parsed.error);
  const err = (field: string): string | undefined =>
    (touched.has(field) || submitted ? liveErrors[field] : undefined) ?? serverFields[field];
  const touch = (field: string) => setTouched((prev) => new Set(prev).add(field));
  const set = <K extends keyof Values>(key: K, value: Values[K]) => {
    setValues((v) => ({ ...v, [key]: value }));
    if (serverFields[key]) setServerFields((f) => ({ ...f, [key]: "" })); // a changed field is no longer the one the server refused
  };

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitted(true);
    setBanner(null);
    setServerFields({});
    if (!parsed.success) return;
    const result = await attempt.run();
    if (!result) return;
    if (result.ok) {
      router.replace("/inventory");
      return;
    }
    const fields = { ...result.fieldErrors };
    if (/already registered/i.test(result.error)) fields.email = "That email already has an account. Sign in instead.";
    setServerFields(fields);
    if (Object.keys(fields).length === 0) setBanner(result.error);
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas p-4">
      <div className="w-full max-w-md">
        <p className="mb-4 text-center text-ui-lg font-semibold text-fg">BazaarFlow</p>
        <form
          onSubmit={onSubmit}
          noValidate
          aria-label="Create your shop"
          className="flex flex-col gap-4 rounded-lg border border-border bg-surface p-6 shadow-popover"
        >
          <div>
            <h1 className="text-ui-xl font-semibold text-fg">Create your shop</h1>
            <p className="text-ui-sm text-fg-muted">One account for you, one shop to run. It takes a minute.</p>
          </div>

          {banner ? (
            <p role="alert" className="rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
              {banner}
            </p>
          ) : null}

          <FormField id="full_name" label="Your name" required error={err("full_name")}>
            <TextInput id="full_name" autoComplete="name" value={values.full_name} onChange={(e) => set("full_name", e.target.value)} onBlur={() => touch("full_name")} invalid={Boolean(err("full_name"))} />
          </FormField>
          <FormField id="shop_name" label="Shop name" required error={err("shop_name")}>
            <TextInput id="shop_name" autoComplete="organization" value={values.shop_name} onChange={(e) => set("shop_name", e.target.value)} onBlur={() => touch("shop_name")} invalid={Boolean(err("shop_name"))} />
          </FormField>
          <FormField id="email" label="Email" required error={err("email")}>
            <TextInput id="email" type="email" autoComplete="email" inputMode="email" value={values.email} onChange={(e) => set("email", e.target.value)} onBlur={() => touch("email")} invalid={Boolean(err("email"))} />
          </FormField>
          <FormField id="password" label="Password" required error={err("password")} hint="At least 8 characters. Avoid common passwords like 12345678.">
            <TextInput id="password" type="password" autoComplete="new-password" value={values.password} onChange={(e) => set("password", e.target.value)} onBlur={() => touch("password")} invalid={Boolean(err("password"))} />
          </FormField>
          <FormField id="phone" label="Phone" required error={err("phone")} hint="We use it for your daily summary. Pakistani numbers need no country code.">
            <TextInput id="phone" type="tel" autoComplete="tel" inputMode="tel" value={values.phone} onChange={(e) => set("phone", e.target.value)} onBlur={() => touch("phone")} invalid={Boolean(err("phone"))} />
          </FormField>
          <FormField id="city" label="City" error={err("city")}>
            <TextInput id="city" autoComplete="address-level2" value={values.city} onChange={(e) => set("city", e.target.value)} onBlur={() => touch("city")} invalid={Boolean(err("city"))} />
          </FormField>

          <div className="flex flex-col gap-1">
            <label className="flex items-start gap-2 text-ui-base text-fg">
              <Checkbox
                className="mt-0.5"
                checked={values.accept_terms}
                onChange={(e) => {
                  set("accept_terms", e.target.checked);
                  touch("accept_terms");
                }}
                aria-invalid={Boolean(err("accept_terms")) || undefined}
              />
              <span>I accept the terms of the BazaarFlow demo.</span>
            </label>
            {err("accept_terms") ? (
              <p role="alert" className="text-ui-xs text-danger">
                {err("accept_terms")}
              </p>
            ) : null}
          </div>

          <Button type="submit" variant="primary" size="lg" loading={attempt.pending} className="w-full">
            {attempt.pending ? "Creating your shop..." : "Create shop"}
          </Button>
        </form>
        <p className="mt-4 text-center text-ui-sm text-fg-muted">
          Already have an account?{" "}
          <Link href="/sign-in" className="font-medium text-action hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
