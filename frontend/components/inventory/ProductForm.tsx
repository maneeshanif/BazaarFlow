"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Button, buttonClass } from "@/components/app/Button";
import { ConfirmDialog } from "@/components/app/ConfirmDialog";
import { Checkbox, TextInput } from "@/components/form/Controls";
import { FormField } from "@/components/form/FormField";
import { FormShell } from "@/components/form/FormShell";
import { useSubmit } from "@/hooks/useSubmit";
import { apiDelete, apiPatch, apiPost } from "@/lib/api/client";
import type { Product } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatDateTime } from "@/lib/format";
import { fieldErrorsOf, productSchema } from "@/lib/validation/product";

type Values = {
  sku: string;
  name: string;
  category: string;
  price: string;
  cost: string;
  qty_on_hand: string;
  reorder_level: string;
  active: boolean;
};

const blank: Values = { sku: "", name: "", category: "", price: "", cost: "", qty_on_hand: "0", reorder_level: "", active: true };

function valuesOf(p: Product): Values {
  return {
    sku: p.sku,
    name: p.name,
    category: p.category ?? "",
    price: p.price,
    cost: p.cost ?? "",
    qty_on_hand: String(p.qty_on_hand),
    reorder_level: String(p.reorder_level),
    active: p.active,
  };
}

/**
 * Create or edit a product (PRD F-010) in the mandated master-form layout. Quantity is set once, as opening stock;
 * after that it only changes through stock movements, so the field is read-only when editing.
 */
export function ProductForm({ product, onSaved }: { product?: Product; onSaved?: (p: Product) => void }) {
  const router = useRouter();
  const { role } = useAuth();
  const editing = Boolean(product);
  const [values, setValues] = useState<Values>(product ? valuesOf(product) : blank);
  // a field shows its message once it has been visited (blur) or a submit was tried, and clears as soon as it is valid
  const [touched, setTouched] = useState<ReadonlySet<string>>(new Set());
  const [submitted, setSubmitted] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const save = useSubmit(async (v: Values) => {
    const body = {
      sku: v.sku.trim(),
      name: v.name.trim(),
      category: v.category.trim() || (editing ? "" : undefined),
      price: v.price.trim(),
      cost: v.cost.trim() === "" ? (editing ? null : undefined) : v.cost.trim(),
      reorder_level: v.reorder_level.trim() === "" ? undefined : Number(v.reorder_level),
      active: v.active,
    };
    return product
      ? apiPatch<Product>(`/inventory/${product.id}`, body)
      : apiPost<Product>("/inventory/", { ...body, qty_on_hand: Number(v.qty_on_hand) });
  });
  const remove = useSubmit(async () => {
    if (product) await apiDelete(`/inventory/${product.id}`);
    return true;
  });

  const set = <K extends keyof Values>(key: K, value: Values[K]) => setValues((v) => ({ ...v, [key]: value }));

  const parsed = useMemo(
    () =>
      productSchema.safeParse({
        sku: values.sku,
        name: values.name,
        category: values.category,
        price: values.price,
        cost: values.cost,
        qty_on_hand: values.qty_on_hand,
        reorder_level: values.reorder_level === "" ? undefined : values.reorder_level,
        active: values.active,
      }),
    [values],
  );
  const liveErrors = parsed.success ? {} : fieldErrorsOf(parsed.error);
  const touch = (field: string) => setTouched((prev) => new Set(prev).add(field));

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitted(true);
    if (!parsed.success) return;
    const saved = await save.run(values);
    if (!saved) return;
    toast.success(editing ? `Saved changes to ${saved.name}` : `Added ${saved.name} with ${saved.qty_on_hand} in stock`);
    onSaved?.(saved);
    if (!editing) router.push("/inventory");
  }

  async function onDelete() {
    const done = await remove.run();
    if (!done) return;
    toast.success(`Deleted ${product?.name ?? "product"}`);
    router.push("/inventory");
  }

  const serverFields = { ...save.fieldErrors };
  if (save.error?.code === "duplicate_sku") serverFields.sku = save.error.message;
  const err = (field: string): string | undefined =>
    (touched.has(field) || submitted ? liveErrors[field] : undefined) ?? serverFields[field];
  const formLevel = save.error && Object.keys(serverFields).length === 0 ? save.error.message : undefined;


  return (
    <form onSubmit={onSubmit} noValidate aria-label={editing ? "Edit product" : "Add product"}>
      <FormShell
        mode="master"
        title={editing ? (product?.name ?? "Edit product") : "Add product"}
        status={product ? (product.active ? "active" : "inactive") : undefined}
        actions={
          <>
            {editing && role === "owner" ? (
              <Button variant="danger" className="mr-auto" onClick={() => setConfirmDelete(true)}>
                Delete product
              </Button>
            ) : null}
            <Link href="/inventory" className={buttonClass("secondary")}>
              Cancel
            </Link>
            <Button type="submit" variant="primary" loading={save.pending}>
              {editing ? "Save changes" : "Add product"}
            </Button>
          </>
        }
        audit={
          product ? (
            <p>
              Added {formatDateTime(product.created_at)}. Last changed {formatDateTime(product.updated_at)}. Every change to this
              product and its stock is recorded in the audit log.
            </p>
          ) : (
            <p>Adding a product is recorded in the audit log, with its opening stock as a stock movement.</p>
          )
        }
      >
        {formLevel ? (
          <p role="alert" className="mb-4 rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
            {formLevel}
          </p>
        ) : null}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <FormField id="sku" label="SKU" required error={err("sku")} hint="Your own code for this product. Must be unique in your shop.">
            <TextInput id="sku" value={values.sku} onChange={(e) => set("sku", e.target.value)} onBlur={() => touch("sku")} invalid={Boolean(err("sku"))} autoComplete="off" className="font-mono" />
          </FormField>
          <FormField id="name" label="Name" required error={err("name")}>
            <TextInput id="name" value={values.name} onChange={(e) => set("name", e.target.value)} onBlur={() => touch("name")} invalid={Boolean(err("name"))} autoComplete="off" />
          </FormField>
          <FormField id="category" label="Category" error={err("category")}>
            <TextInput id="category" value={values.category} onChange={(e) => set("category", e.target.value)} onBlur={() => touch("category")} invalid={Boolean(err("category"))} />
          </FormField>
          <FormField id="price" label="Price (Rs)" required error={err("price")}>
            <TextInput id="price" inputMode="decimal" value={values.price} onChange={(e) => set("price", e.target.value)} onBlur={() => touch("price")} invalid={Boolean(err("price"))} className="text-right font-mono tabular-nums" />
          </FormField>
          <FormField id="cost" label="Cost (Rs)" error={err("cost")} hint="Used to work out profit. Staff cannot see it.">
            <TextInput id="cost" inputMode="decimal" value={values.cost} onChange={(e) => set("cost", e.target.value)} onBlur={() => touch("cost")} invalid={Boolean(err("cost"))} className="text-right font-mono tabular-nums" />
          </FormField>
          <FormField
            id="qty_on_hand"
            label={editing ? "In stock" : "Opening stock"}
            required={!editing}
            error={err("qty_on_hand")}
            hint={editing ? "Change it with a stock movement below, so the history stays complete." : undefined}
          >
            <TextInput
              id="qty_on_hand"
              inputMode="numeric"
              value={product ? String(product.qty_on_hand) : values.qty_on_hand}
              readOnly={editing}
              onChange={(e) => set("qty_on_hand", e.target.value)}
              onBlur={() => touch("qty_on_hand")}
              invalid={Boolean(err("qty_on_hand"))}
              className="text-right font-mono tabular-nums"
            />
          </FormField>
          <FormField id="reorder_level" label="Reorder at" error={err("reorder_level")} hint="You will see a low-stock warning at or below this quantity.">
            <TextInput id="reorder_level" inputMode="numeric" value={values.reorder_level} onChange={(e) => set("reorder_level", e.target.value)} onBlur={() => touch("reorder_level")} invalid={Boolean(err("reorder_level"))} className="text-right font-mono tabular-nums" />
          </FormField>
          <div className="flex items-end">
            <label className="flex h-control-md items-center gap-2 text-ui-base text-fg">
              <Checkbox checked={values.active} onChange={(e) => set("active", e.target.checked)} />
              Available for sale
            </label>
          </div>
        </div>
      </FormShell>

      {product ? (
        <ConfirmDialog
          open={confirmDelete}
          onOpenChange={setConfirmDelete}
          title={`Delete ${product.name}?`}
          confirmLabel="Delete product"
          pending={remove.pending}
          onConfirm={() => void onDelete()}
        >
          <p>
            {product.name} ({product.sku}) will disappear from your product list and new sales. Past orders and the stock history
            keep their record of it.
          </p>
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
