"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";
import { FormField } from "@/components/form/FormField";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/lib/auth/AuthProvider";
import { safeNextPath } from "@/lib/auth/jwt";

const buttonClass =
  "inline-flex h-control-lg w-full items-center justify-center rounded-md bg-action px-4 text-ui-base font-medium text-fg-inverse hover:bg-action-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-focus disabled:cursor-not-allowed disabled:opacity-60";

function SignInForm() {
  const { login } = useAuth();
  const router = useRouter();
  const next = safeNextPath(useSearchParams().get("next")) ?? "/dashboard";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenantId, setTenantId] = useState("");
  const [tenants, setTenants] = useState<{ tenant_id: string; tenant_name: string }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const result = await login(email, password, tenantId || undefined);
    setBusy(false);
    if (result.ok) {
      router.replace(next);
      return;
    }
    if (result.tenants) {
      setTenants(result.tenants);
      setTenantId(result.tenants[0]?.tenant_id ?? "");
    }
    setError(result.error);
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas p-4">
      <form
        onSubmit={submit}
        aria-label="Sign in"
        className="flex w-full max-w-sm flex-col gap-4 rounded-lg border border-border bg-surface p-6 shadow-popover"
      >
        <div>
          <h1 className="text-ui-xl font-semibold text-fg">Sign in to BazaarFlow</h1>
          <p className="text-ui-sm text-fg-muted">Use the email and password you registered your shop with.</p>
        </div>

        <FormField id="email" label="Email" required>
          <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </FormField>
        <FormField id="password" label="Password" required>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </FormField>

        {tenants.length > 0 ? (
          <FormField id="shop" label="Shop" required hint="Your account belongs to more than one shop.">
            <select
              id="shop"
              value={tenantId}
              onChange={(e) => setTenantId(e.target.value)}
              className="h-control-md w-full rounded-md border border-border bg-surface px-3 text-ui-base text-fg"
            >
              {tenants.map((t) => (
                <option key={t.tenant_id} value={t.tenant_id}>
                  {t.tenant_name}
                </option>
              ))}
            </select>
          </FormField>
        ) : null}

        {error ? (
          <p role="alert" className="rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
            {error}
          </p>
        ) : null}

        <button type="submit" disabled={busy} className={buttonClass}>
          {busy ? "Signing in..." : "Sign in"}
        </button>
      </form>
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
