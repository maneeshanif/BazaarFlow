"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState, type FormEvent } from "react";
import { Button } from "@/components/app/Button";
import { SelectInput, TextInput } from "@/components/form/Controls";
import { FormField } from "@/components/form/FormField";
import { useSubmit } from "@/hooks/useSubmit";
import { useAuth, type LoginResult } from "@/lib/auth/AuthProvider";
import { safeNextPath } from "@/lib/auth/jwt";
import { signInSchema } from "@/lib/validation/auth";
import { fieldErrorsOf } from "@/lib/validation/common";

type Shop = { tenant_id: string; tenant_name: string };

/** Sign in (PRD F-001): email, password and, only for accounts that belong to several shops, which shop to open. */
function SignInForm() {
  const { login } = useAuth();
  const router = useRouter();
  const next = safeNextPath(useSearchParams().get("next")) ?? "/dashboard";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenantId, setTenantId] = useState("");
  const [shops, setShops] = useState<Shop[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [touched, setTouched] = useState<ReadonlySet<string>>(new Set());
  const [submitted, setSubmitted] = useState(false);

  const attempt = useSubmit((): Promise<LoginResult> => login(email.trim(), password, tenantId || undefined));

  const parsed = useMemo(() => signInSchema.safeParse({ email, password }), [email, password]);
  const liveErrors = parsed.success ? {} : fieldErrorsOf(parsed.error);
  const err = (field: string): string | undefined => (touched.has(field) || submitted ? liveErrors[field] : undefined);
  const touch = (field: string) => setTouched((prev) => new Set(prev).add(field));

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitted(true);
    setMessage(null);
    if (!parsed.success) return;
    const result = await attempt.run();
    if (!result) return;
    if (result.ok) {
      router.replace(next);
      return;
    }
    if (result.tenants) {
      setShops(result.tenants);
      setTenantId(result.tenants[0]?.tenant_id ?? "");
    }
    setMessage(result.error);
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas p-4">
      <div className="w-full max-w-sm">
        <p className="mb-4 text-center text-ui-lg font-semibold text-fg">BazaarFlow</p>
        <form
          onSubmit={submit}
          noValidate
          aria-label="Sign in"
          className="flex flex-col gap-4 rounded-lg border border-border bg-surface p-6 shadow-popover"
        >
          <div>
            <h1 className="text-ui-xl font-semibold text-fg">Sign in</h1>
            <p className="text-ui-sm text-fg-muted">Use the email and password you registered your shop with.</p>
          </div>

          <FormField id="email" label="Email" required error={err("email")}>
            <TextInput
              id="email"
              type="email"
              autoComplete="email"
              inputMode="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onBlur={() => touch("email")}
              invalid={Boolean(err("email"))}
            />
          </FormField>
          <FormField id="password" label="Password" required error={err("password")}>
            <TextInput
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onBlur={() => touch("password")}
              invalid={Boolean(err("password"))}
            />
          </FormField>

          {shops.length > 0 ? (
            <FormField id="shop" label="Shop" required hint="Your account belongs to more than one shop.">
              <SelectInput id="shop" value={tenantId} onChange={(e) => setTenantId(e.target.value)}>
                {shops.map((s) => (
                  <option key={s.tenant_id} value={s.tenant_id}>
                    {s.tenant_name}
                  </option>
                ))}
              </SelectInput>
            </FormField>
          ) : null}

          {message ? (
            <p role="alert" className="rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
              {message}
            </p>
          ) : null}

          <Button type="submit" variant="primary" size="lg" loading={attempt.pending} className="w-full">
            {attempt.pending ? "Signing in..." : "Sign in"}
          </Button>
        </form>
        <p className="mt-4 text-center text-ui-sm text-fg-muted">
          New to BazaarFlow?{" "}
          <Link href="/register" className="font-medium text-action hover:underline">
            Create your shop
          </Link>
        </p>
      </div>
    </main>
  );
}

export default function SignInPage() {
  return (
    <Suspense>
      <SignInForm />
    </Suspense>
  );
}
