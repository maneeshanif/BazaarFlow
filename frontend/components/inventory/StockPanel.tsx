"use client";

import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Button } from "@/components/app/Button";
import { DataTable, type Column } from "@/components/app/DataTable";
import { SelectInput, TextInput } from "@/components/form/Controls";
import { FormField } from "@/components/form/FormField";
import { useLoad } from "@/hooks/useLoad";
import { useSubmit } from "@/hooks/useSubmit";
import { apiGet, apiPost } from "@/lib/api/client";
import type { Page, Product, StockMovement } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { fieldErrorsOf, stockMovementSchema } from "@/lib/validation/product";

const REASONS = [
  { value: "purchase", label: "Restock (bought more)" },
  { value: "adjustment", label: "Correction (count was off)" },
  { value: "return", label: "Customer return" },
];

type Row = StockMovement & { change: number; when: string; reason_label: string };

const columns: Column<Row>[] = [
  { key: "when", header: "When" },
  { key: "reason_label", header: "Reason" },
  { key: "change", header: "Change", numeric: true },
  { key: "note", header: "Note" },
  { key: "actor_type", header: "By" },
];

/** Manual stock changes for one product plus its movement history. Managers and owners only (the API enforces it). */
export function StockPanel({ product, onChanged }: { product: Product; onChanged: (p: Product) => void }) {
  const [delta, setDelta] = useState("");
  const [reason, setReason] = useState("purchase");
  const [note, setNote] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const history = useLoad(
    () => apiGet<Page<StockMovement>>(`/inventory/${product.id}/stock-movements`, { limit: 20 }),
    [product.id, product.qty_on_hand],
    (page) => page.items.length === 0,
  );

  const move = useSubmit((body: { delta: number; reason: string; note?: string }) =>
    apiPost<Product>(`/inventory/${product.id}/stock-movements`, body),
  );

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const parsed = stockMovementSchema.safeParse({ delta, reason, note: note || undefined });
    if (!parsed.success) {
      setErrors(fieldErrorsOf(parsed.error));
      return;
    }
    setErrors({});
    const updated = await move.run({ delta: parsed.data.delta, reason: parsed.data.reason, note: parsed.data.note });
    if (!updated) return;
    toast.success(`${product.name} now has ${updated.qty_on_hand} in stock`);
    setDelta("");
    setNote("");
    onChanged(updated);
  }

  const fieldError = (name: string): string | undefined => errors[name] ?? move.fieldErrors[name];
  const refused = move.error && Object.keys(move.fieldErrors).length === 0 ? move.error.message : undefined;
  const rows: Row[] = (history.data?.items ?? []).map((m) => ({
    ...m,
    change: m.delta,
    when: formatDateTime(m.created_at),
    reason_label: m.reason,
  }));

  return (
    <section aria-label="Stock movements" className="flex max-w-form flex-col gap-4">
      <h2 className="text-ui-md font-semibold text-fg">Change stock</h2>
      <form onSubmit={onSubmit} noValidate className="flex flex-col gap-3 rounded-lg border border-border bg-surface p-4">
        {refused ? (
          <p role="alert" className="rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
            {refused}
          </p>
        ) : null}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <FormField id="delta" label="Quantity change" required error={fieldError("delta")} hint="Use a minus sign to take stock out, like -3.">
            <TextInput id="delta" inputMode="numeric" value={delta} onChange={(e) => setDelta(e.target.value)} invalid={Boolean(fieldError("delta"))} className="text-right font-mono tabular-nums" />
          </FormField>
          <FormField id="reason" label="Reason" required error={fieldError("reason")}>
            <SelectInput id="reason" value={reason} onChange={(e) => setReason(e.target.value)}>
              {REASONS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </SelectInput>
          </FormField>
          <FormField id="note" label="Note" error={fieldError("note")}>
            <TextInput id="note" value={note} onChange={(e) => setNote(e.target.value)} invalid={Boolean(fieldError("note"))} />
          </FormField>
        </div>
        <div className="flex justify-end">
          <Button type="submit" variant="primary" loading={move.pending}>
            Record stock change
          </Button>
        </div>
      </form>

      <h2 className="text-ui-md font-semibold text-fg">Stock history</h2>
      <DataTable
        caption={`Stock history for ${product.name}`}
        columns={columns}
        rows={rows}
        state={history.state}
        rowKey={(r) => r.id}
        emptyMessage="No stock changes recorded yet."
        errorMessage={history.error?.message ?? "Could not load the stock history."}
        onRetry={history.reload}
      />
    </section>
  );
}
