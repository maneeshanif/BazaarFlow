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
import type { ShopVendor } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatDateTime } from "@/lib/format";
import { fieldErrorsOf } from "@/lib/validation/common";
import { vendorSchema } from "@/lib/validation/vendor";

type Values = { name: string; phone: string };

/** Create or edit a vendor (PRD F-012) in the mandated master-form layout. */
export function VendorForm({ vendor, onSaved }: { vendor?: ShopVendor; onSaved?: (v: ShopVendor) => void }) {
  const router = useRouter();
  const { role } = useAuth();
  const editing = Boolean(vendor);
  const [values, setValues] = useState<Values>(vendor ? { name: vendor.name, phone: vendor.phone ?? "" } : { name: "", phone: "+92" });
  const [touched, setTouched] = useState<ReadonlySet<string>>(new Set());
  const [submitted, setSubmitted] = useState(false);
  const [created, setCreated] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const save = useSubmit(async (v: Values) => {
    const parsedBody = vendorSchema.parse(v);
    const body = { name: parsedBody.name, phone: parsedBody.phone };
    return vendor ? apiPatch<ShopVendor>(`/vendors/${vendor.id}`, body) : apiPost<ShopVendor>("/vendors/", body);
  });
  const remove = useSubmit(async () => {
    if (vendor) await apiDelete(`/vendors/${vendor.id}`);
    return true;
  });

  const parsed = useMemo(() => vendorSchema.safeParse(values), [values]);
  const liveErrors = parsed.success ? {} : fieldErrorsOf(parsed.error);
  const err = (field: string): string | undefined => (touched.has(field) || submitted ? liveErrors[field] : undefined) ?? save.fieldErrors[field];
  const touch = (field: string) => setTouched((prev) => new Set(prev).add(field));
  const set = <K extends keyof Values>(key: K, value: string) => setValues((v) => ({ ...v, [key]: value }));
  const formLevel = save.error && Object.keys(save.fieldErrors).length === 0 ? save.error.message : undefined;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (created) return;
    setSubmitted(true);
    if (!parsed.success) return;
    const saved = await save.run(values);
    if (!saved) return;
    if (!editing) setCreated(true);
    toast.success(editing ? `Saved changes to ${saved.name}` : `Added ${saved.name}`);
    onSaved?.(saved);
    if (!editing) router.push(`/vendors/${saved.id}`);
  }

  async function onDelete() {
    const done = await remove.run();
    if (!done) return;
    toast.success(`Deleted ${vendor?.name ?? "vendor"}`);
    router.push("/vendors");
  }

  return (
    <form onSubmit={onSubmit} noValidate aria-label={editing ? "Edit vendor" : "Add vendor"}>
      <FormShell
        mode="master"
        title={editing ? (vendor?.name ?? "Vendor") : "Add vendor"}
        actions={
          <>
            {editing && role === "owner" ? (
              <Button variant="danger" className="mr-auto" onClick={() => setConfirmDelete(true)}>
                Delete vendor
              </Button>
            ) : null}
            <Link href="/vendors" className={buttonClass("secondary")}>
              Cancel
            </Link>
            <Button type="submit" variant="primary" loading={save.pending} disabled={created}>
              {editing ? "Save changes" : "Add vendor"}
            </Button>
          </>
        }
        audit={
          vendor ? (
            <p>
              Added {formatDateTime(vendor.created_at)}. Last changed {formatDateTime(vendor.updated_at)}. Bills and payments are recorded in the
              audit log.
            </p>
          ) : (
            <p>Adding a vendor is recorded in the audit log.</p>
          )
        }
      >
        {formLevel ? (
          <p role="alert" className="mb-4 rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
            {formLevel}
          </p>
        ) : null}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <FormField id="vendor-name" label="Name" required error={err("name")}>
            <TextInput id="vendor-name" autoComplete="off" value={values.name} onChange={(e) => set("name", e.target.value)} onBlur={() => touch("name")} invalid={Boolean(err("name"))} />
          </FormField>
          <FormField id="vendor-phone" label="Phone" error={err("phone")} hint="Their WhatsApp number, used when you message them about a reorder.">
            <TextInput id="vendor-phone" type="tel" inputMode="tel" value={values.phone} onChange={(e) => set("phone", e.target.value)} onBlur={() => touch("phone")} invalid={Boolean(err("phone"))} className="font-mono" />
          </FormField>
        </div>
      </FormShell>

      {vendor ? (
        <ConfirmDialog
          open={confirmDelete}
          onOpenChange={setConfirmDelete}
          title={`Delete ${vendor.name}?`}
          confirmLabel="Delete vendor"
          pending={remove.pending}
          onConfirm={() => void onDelete()}
        >
          <p>{vendor.name} will disappear from your vendor list. A vendor you still owe money to cannot be deleted.</p>
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
