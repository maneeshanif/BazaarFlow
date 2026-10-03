"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/app/Button";
import { LookupDialog } from "@/components/app/LookupDialog";
import { TextInput } from "@/components/form/Controls";
import { FormField } from "@/components/form/FormField";
import { useSubmit } from "@/hooks/useSubmit";
import { apiGet, apiPost } from "@/lib/api/client";
import type { Customer, Page } from "@/lib/api/types";
import { normalizePhone } from "@/lib/validation/register";

export type CustomerChoice = { id: string; label: string };

const labelOf = (c: Customer): string => c.name || c.phone;

/** The customer of a sale: walk-in by default, found by name or phone, or added on the spot (staff may add customers). */
export function CustomerLookup({ value, onChange, error }: { value: CustomerChoice | null; onChange: (c: CustomerChoice | null) => void; error?: string }) {
  const [open, setOpen] = useState(false);
  const [adding, setAdding] = useState(false);
  const [phone, setPhone] = useState("+92");
  const [name, setName] = useState("");
  const create = useSubmit((body: { phone: string; name: string }) => apiPost<Customer>("/customers/", body));

  async function add() {
    const made = await create.run({ phone: normalizePhone(phone), name: name.trim() });
    if (!made) return;
    toast.success(`Added ${labelOf(made)}`);
    onChange({ id: made.id, label: labelOf(made) });
    setAdding(false);
    setOpen(false);
    setPhone("+92");
    setName("");
  }

  return (
    <FormField id="customer" label="Customer" error={error} hint={value ? undefined : "Leave as walk-in for a customer you do not need to remember."}>
      <div className="flex items-center gap-2">
        <Button
          id="customer"
          className="min-w-0 flex-1 justify-start truncate"
          onClick={() => setOpen(true)}
          aria-haspopup="dialog"
          aria-label={`Customer: ${value ? value.label : "Walk-in customer"}. Change`}
        >
          {value ? value.label : "Walk-in customer"}
        </Button>
        {value ? (
          <Button variant="ghost" onClick={() => onChange(null)} aria-label="Remove customer, sell to a walk-in">
            Clear
          </Button>
        ) : null}
      </div>
      <LookupDialog<Customer>
        open={open}
        onOpenChange={(next) => {
          setOpen(next);
          if (!next) setAdding(false);
        }}
        title="Find a customer"
        description="Search by name or phone number."
        placeholder="Name or phone"
        load={async (q) => (await apiGet<Page<Customer>>("/customers/", { q, limit: 20 })).items}
        keyOf={(c) => c.id}
        render={(c) => (
          <span className="flex flex-col">
            <span className="font-medium">{labelOf(c)}</span>
            <span className="font-mono text-ui-xs text-fg-muted">{c.phone}</span>
          </span>
        )}
        onSelect={(c) => onChange({ id: c.id, label: labelOf(c) })}
        emptyMessage="No customer matches. Add them below."
        footer={
          adding ? (
            <div className="flex flex-col gap-3 rounded-md border border-border p-3">
              {create.error ? (
                <p role="alert" className="text-ui-sm text-danger">
                  {create.error.message}
                </p>
              ) : null}
              <FormField id="new-customer-phone" label="Phone" required>
                <TextInput id="new-customer-phone" type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} className="font-mono" />
              </FormField>
              <FormField id="new-customer-name" label="Name">
                <TextInput id="new-customer-name" value={name} onChange={(e) => setName(e.target.value)} />
              </FormField>
              <div className="flex justify-end gap-2">
                <Button onClick={() => setAdding(false)}>Cancel</Button>
                <Button variant="primary" loading={create.pending} onClick={() => void add()}>
                  Add customer
                </Button>
              </div>
            </div>
          ) : (
            <Button onClick={() => setAdding(true)}>Add a new customer</Button>
          )
        }
      />
    </FormField>
  );
}
