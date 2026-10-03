"use client";

import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Button } from "@/components/app/Button";
import { DataTable, type Column } from "@/components/app/DataTable";
import { StatusBadge } from "@/components/app/StatusBadge";
import { SelectInput, TextInput } from "@/components/form/Controls";
import { FormField } from "@/components/form/FormField";
import { useLoad } from "@/hooks/useLoad";
import { useSubmit } from "@/hooks/useSubmit";
import { apiGet, apiPost } from "@/lib/api/client";
import type { Customer, LedgerEntry, Page, Payment } from "@/lib/api/types";
import { formatDateTime, formatMoney } from "@/lib/format";
import { fieldErrorsOf } from "@/lib/validation/common";
import { paymentSchema } from "@/lib/validation/customer";

const METHODS = [
  { value: "cash", label: "Cash" },
  { value: "card", label: "Card" },
  { value: "bank", label: "Bank transfer" },
  { value: "wallet", label: "Easypaisa or JazzCash" },
];

type Row = LedgerEntry & { when: string; what: string; change: string };

const columns: Column<Row>[] = [
  { key: "when", header: "When" },
  { key: "what", header: "What happened" },
  { key: "change", header: "Amount", money: true },
  { key: "balance_after", header: "They owed after", money: true },
];

const refLabel = (e: LedgerEntry): string => {
  if (e.ref_type === "payment") return "Payment received";
  if (e.ref_type === "order") return e.direction === "debit" ? "Sale on credit" : "Sale reversed";
  return e.direction === "debit" ? "Added to what they owe" : "Credit";
};

/** The udhaar ledger of one customer: what they owe, a way to record a payment, and every entry with a running balance. */
export function LedgerPanel({ customer, onChanged }: { customer: Customer; onChanged: (balance: string) => void }) {
  const balance = customer.balance ?? "0.00";
  const owes = Number(balance) > 0;
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("cash");
  const [touched, setTouched] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const ledger = useLoad(
    () => apiGet<Page<LedgerEntry>>(`/customers/${customer.id}/ledger`, { limit: 25 }),
    [customer.id, balance],
    (page) => page.items.length === 0,
  );
  const pay = useSubmit((body: { amount: string; method: string }) => apiPost<Payment>(`/customers/${customer.id}/payments`, body));

  const parsed = paymentSchema.safeParse({ amount, method });
  const live = parsed.success ? {} : fieldErrorsOf(parsed.error);
  const overpay = parsed.success && Number(amount) > Number(balance) ? `They only owe ${formatMoney(balance)}` : undefined;
  const err = (field: string): string | undefined => ((touched || submitted) && live[field]) || (field === "amount" ? overpay : undefined) || pay.fieldErrors[field];
  const refused = pay.error && Object.keys(pay.fieldErrors).length === 0 ? pay.error.message : undefined;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitted(true);
    if (!parsed.success || overpay) return;
    const done = await pay.run({ amount: parsed.data.amount, method: parsed.data.method });
    if (!done) return;
    toast.success(`Recorded ${formatMoney(done.amount)}. They now owe ${formatMoney(done.balance)}`);
    setAmount("");
    setTouched(false);
    setSubmitted(false);
    onChanged(done.balance);
  }

  const rows: Row[] = (ledger.data?.items ?? []).map((e) => ({
    ...e,
    when: formatDateTime(e.created_at),
    what: refLabel(e),
    change: e.direction === "credit" ? `-${e.amount}` : e.amount,
  }));

  return (
    <section aria-label="Udhaar" className="flex max-w-form flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-surface p-4">
        <div>
          <h2 className="text-ui-md font-semibold text-fg">Udhaar</h2>
          <p className="text-ui-sm text-fg-muted">What this customer owes you for sales on credit.</p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={owes ? "owes" : "settled"} />
          <p aria-label="Balance" className="font-mono text-ui-xl font-semibold tabular-nums text-fg">
            {formatMoney(balance)}
          </p>
        </div>
      </div>

      {owes ? (
        <form onSubmit={onSubmit} noValidate aria-label="Record a payment" className="flex flex-col gap-3 rounded-lg border border-border bg-surface p-4">
          <h3 className="text-ui-base font-semibold text-fg">Record a payment</h3>
          {refused ? (
            <p role="alert" className="rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
              {refused}
            </p>
          ) : null}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <FormField id="payment-amount" label="Amount received (Rs)" required error={err("amount")}>
              <TextInput id="payment-amount" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} onBlur={() => setTouched(true)} invalid={Boolean(err("amount"))} className="text-right font-mono tabular-nums" />
            </FormField>
            <FormField id="payment-method" label="Paid by" required error={err("method")}>
              <SelectInput id="payment-method" value={method} onChange={(e) => setMethod(e.target.value)}>
                {METHODS.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </SelectInput>
            </FormField>
          </div>
          <div className="flex justify-end">
            <Button type="submit" variant="primary" loading={pay.pending}>
              Record payment
            </Button>
          </div>
        </form>
      ) : null}

      <DataTable
        caption={`Udhaar ledger for ${customer.name ?? customer.phone}`}
        columns={columns}
        rows={rows}
        state={ledger.state}
        rowKey={(r) => r.id}
        emptyMessage="No credit sales or payments yet."
        errorMessage={ledger.error?.message ?? "Could not load the ledger."}
        onRetry={ledger.reload}
      />
    </section>
  );
}
