"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Button, buttonClass } from "@/components/app/Button";
import { ConfirmDialog } from "@/components/app/ConfirmDialog";
import { TextInput } from "@/components/form/Controls";
import { FormField } from "@/components/form/FormField";
import { FormShell } from "@/components/form/FormShell";
import { useSubmit } from "@/hooks/useSubmit";
import { apiDelete, apiPatch, apiPost } from "@/lib/api/client";
import type { Customer } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatDateTime } from "@/lib/format";
import { customerSchema } from "@/lib/validation/customer";
import { fieldErrorsOf } from "@/lib/validation/common";
import { normalizePhone } from "@/lib/validation/register";

type Values = { phone: string; name: string; email: string; address: string };
const blank: Values = { phone: "+92", name: "", email: "", address: "" };

/** Create or edit a customer (PRD F-009) in the mandated master-form layout. */
export function CustomerForm({ customer, onSaved }: { customer?: Customer; onSaved?: (c: Customer) => void }) {
  const router = useRouter();
  const { role } = useAuth();
  const editing = Boolean(customer);
  const [values, setValues] = useState<Values>(
    customer ? { phone: customer.phone, name: customer.name ?? "", email: customer.email ?? "", address: customer.address ?? "" } : blank,
  );
  const [touched, setTouched] = useState<ReadonlySet<string>>(new Set());
  const [submitted, setSubmitted] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const save = useSubmit(async (v: Values) => {
    const body = {
      phone: normalizePhone(v.phone),
      name: v.name.trim(),
      email: v.email.trim(),
      address: v.address.trim(),
    };
    return customer ? apiPatch<Customer>(`/customers/${customer.id}`, body) : apiPost<Customer>("/customers/", body);
  });
  const remove = useSubmit(async () => {
    if (customer) await apiDelete(`/customers/${customer.id}`);
    return true;
  });

  const parsed = useMemo(() => customerSchema.safeParse(values), [values]);
  const liveErrors = parsed.success ? {} : fieldErrorsOf(parsed.error);
  const serverFields = { ...save.fieldErrors };
  if (save.error?.code === "duplicate_phone") serverFields.phone = save.error.message;
  const err = (field: string): string | undefined =>
    (touched.has(field) || submitted ? liveErrors[field] : undefined) ?? serverFields[field];
  const touch = (field: string) => setTouched((prev) => new Set(prev).add(field));
  const set = <K extends keyof Values>(key: K, value: string) => setValues((v) => ({ ...v, [key]: value }));
  const formLevel = save.error && Object.keys(serverFields).length === 0 ? save.error.message : undefined;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitted(true);
    if (!parsed.success) return;
    const saved = await save.run(values);
    if (!saved) return;
    toast.success(editing ? `Saved changes to ${saved.name ?? saved.phone}` : `Added ${saved.name ?? saved.phone}`);
    onSaved?.(saved);
    if (!editing) router.push(`/customers/${saved.id}`);
  }

  async function onDelete() {
    const done = await remove.run();
    if (!done) return;
    toast.success(`Deleted ${customer?.name ?? customer?.phone ?? "customer"}`);
    router.push("/customers");
  }

  const label = customer ? (customer.name ?? customer.phone) : "";

  return (
    <form onSubmit={onSubmit} noValidate aria-label={editing ? "Edit customer" : "Add customer"}>
      <FormShell
        mode="master"
        title={editing ? label : "Add customer"}
        actions={
          <>
            {editing && role === "owner" ? (
              <Button variant="danger" className="mr-auto" onClick={() => setConfirmDelete(true)}>
                Delete customer
              </Button>
            ) : null}
            <Link href="/customers" className={buttonClass("secondary")}>
              Cancel
            </Link>
            <Button type="submit" variant="primary" loading={save.pending}>
              {editing ? "Save changes" : "Add customer"}
            </Button>
          </>
        }
        audit={
          customer ? (
            <p>
              Added {formatDateTime(customer.created_at)}. Last changed {formatDateTime(customer.updated_at)}. Changes and payments are
              recorded in the audit log.
            </p>
          ) : (
            <p>Adding a customer is recorded in the audit log.</p>
          )
        }
      >
        {formLevel ? (
          <p role="alert" className="mb-4 rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
            {formLevel}
          </p>
        ) : null}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <FormField id="phone" label="Phone" required error={err("phone")} hint="Their WhatsApp number is best. Pakistani numbers need no country code.">
            <TextInput id="phone" type="tel" inputMode="tel" value={values.phone} onChange={(e) => set("phone", e.target.value)} onBlur={() => touch("phone")} invalid={Boolean(err("phone"))} className="font-mono" />
          </FormField>
          <FormField id="name" label="Name" error={err("name")}>
            <TextInput id="name" autoComplete="off" value={values.name} onChange={(e) => set("name", e.target.value)} onBlur={() => touch("name")} invalid={Boolean(err("name"))} />
          </FormField>
          <FormField id="email" label="Email" error={err("email")}>
            <TextInput id="email" type="email" value={values.email} onChange={(e) => set("email", e.target.value)} onBlur={() => touch("email")} invalid={Boolean(err("email"))} />
          </FormField>
          <FormField id="address" label="Address" error={err("address")} className="md:col-span-2">
            <TextInput id="address" value={values.address} onChange={(e) => set("address", e.target.value)} onBlur={() => touch("address")} invalid={Boolean(err("address"))} />
          </FormField>
        </div>
      </FormShell>

      {customer ? (
        <ConfirmDialog
          open={confirmDelete}
          onOpenChange={setConfirmDelete}
          title={`Delete ${label}?`}
          confirmLabel="Delete customer"
          pending={remove.pending}
          onConfirm={() => void onDelete()}
        >
          <p>{label} will disappear from your customer list. Their past orders keep their record.</p>
          {remove.error ? (
            <p role="alert" className="mt-2 text-danger">
              {remove.error.message}
            </p>
          ) : null}
        </ConfirmDialog>
      ) : null}
    </form>
  );
}
