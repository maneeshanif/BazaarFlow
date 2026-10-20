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
import type { Page, ShopVendor, VendorBill, VendorLedgerEntry, VendorPayment } from "@/lib/api/types";
import { formatDateTime, formatMoney } from "@/lib/format";
import { fieldErrorsOf } from "@/lib/validation/common";
import { billSchema, vendorPaymentSchema } from "@/lib/validation/vendor";

const METHODS = [
  { value: "cash", label: "Cash" },
  { value: "card", label: "Card" },
  { value: "bank", label: "Bank transfer" },
  { value: "wallet", label: "Easypaisa or JazzCash" },
];

type Row = VendorLedgerEntry & { when: string; what: string; change: string };

const columns: Column<Row>[] = [
  { key: "when", header: "When" },
  { key: "what", header: "What happened" },
  { key: "change", header: "Amount", money: true },
  { key: "balance_after", header: "You owed after", money: true },
];

const refLabel = (e: VendorLedgerEntry): string => {
  if (e.ref_type === "vendor_bill") return "Bill received";
  if (e.ref_type === "vendor_payment") return "Payment made";
  return e.direction === "debit" ? "Added to what you owe" : "Credit";
};

/** What the shop owes one vendor: the balance, a way to add a bill or record a payment, and the ledger behind it. */
export function PayablesPanel({ vendor, onChanged }: { vendor: ShopVendor; onChanged: (balance: string) => void }) {
  const balance = vendor.balance;
  const owes = Number(balance) > 0;
  const [bill, setBill] = useState({ amount: "", due_date: "", reference: "", note: "" });
  const [billSubmitted, setBillSubmitted] = useState(false);
  const [payment, setPayment] = useState({ amount: "", method: "cash" });
  const [paySubmitted, setPaySubmitted] = useState(false);

  const ledger = useLoad(
    () => apiGet<Page<VendorLedgerEntry>>(`/vendors/${vendor.id}/ledger`, { limit: 25 }),
    [vendor.id, balance],
    (page) => page.items.length === 0,
  );
  const addBill = useSubmit((body: { amount: string; due_date: string; reference: string; note: string }) =>
    apiPost<VendorBill>(`/vendors/${vendor.id}/bills`, { ...body, due_date: body.due_date || null }),
  );
  const pay = useSubmit((body: { amount: string; method: string }) => apiPost<VendorPayment>(`/vendors/${vendor.id}/payments`, body));

  const billParsed = billSchema.safeParse(bill);
  const billLive = billParsed.success ? {} : fieldErrorsOf(billParsed.error);
  const billErr = (field: string): string | undefined => (billSubmitted ? billLive[field] : undefined) ?? addBill.fieldErrors[field];
  const billRefused = addBill.error && Object.keys(addBill.fieldErrors).length === 0 ? addBill.error.message : undefined;

  const payParsed = vendorPaymentSchema.safeParse(payment);
  const payLive = payParsed.success ? {} : fieldErrorsOf(payParsed.error);
  const overpay = payParsed.success && Number(payment.amount) > Number(balance) ? `You only owe ${formatMoney(balance)}` : undefined;
  const payErr = (field: string): string | undefined => (paySubmitted ? payLive[field] : undefined) ?? (field === "amount" ? overpay : undefined) ?? pay.fieldErrors[field];
  const payRefused = pay.error && Object.keys(pay.fieldErrors).length === 0 ? pay.error.message : undefined;

  async function onBill(event: FormEvent) {
    event.preventDefault();
    setBillSubmitted(true);
    if (!billParsed.success) return;
    const done = await addBill.run(billParsed.data);
    if (!done) return;
    toast.success(`Added a bill of ${formatMoney(done.amount)}. You now owe ${formatMoney(done.balance)}`);
    setBill({ amount: "", due_date: "", reference: "", note: "" });
    setBillSubmitted(false);
    onChanged(done.balance);
  }

  async function onPay(event: FormEvent) {
    event.preventDefault();
    setPaySubmitted(true);
    if (!payParsed.success || overpay) return;
    const done = await pay.run(payParsed.data);
    if (!done) return;
    toast.success(`Paid ${formatMoney(done.amount)}. You now owe ${formatMoney(done.balance)}`);
    setPayment({ amount: "", method: "cash" });
    setPaySubmitted(false);
    onChanged(done.balance);
  }

  const rows: Row[] = (ledger.data?.items ?? []).map((e) => ({
    ...e,
    when: formatDateTime(e.created_at),
    what: refLabel(e),
    change: e.direction === "credit" ? `-${e.amount}` : e.amount,
  }));

  const alert = (message: string | undefined) =>
    message ? (
      <p role="alert" className="rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
        {message}
      </p>
    ) : null;

  return (
    <section aria-label="Payables" className="flex max-w-form flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-card border-2 border-line-strong bg-surface-raised p-6 shadow-card">
        <div>
          <h2 className="text-ui-md font-semibold text-fg">Payables</h2>
          <p className="text-ui-sm text-fg-muted">What you owe this vendor for stock you bought on credit.</p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={owes ? "owes" : "settled"} />
          <p aria-label="Balance" className="font-mono text-ui-xl font-semibold tabular-nums text-fg">
            {formatMoney(balance)}
          </p>
        </div>
      </div>

      <form onSubmit={onBill} noValidate aria-label="Add a bill" className="flex flex-col gap-3 rounded-card border-2 border-line-strong bg-surface-raised p-6 shadow-card">
        <h3 className="text-ui-base font-semibold text-fg">Add a bill</h3>
        {alert(billRefused)}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <FormField id="bill-amount" label="Bill amount (Rs)" required error={billErr("amount")}>
            <TextInput id="bill-amount" inputMode="decimal" value={bill.amount} onChange={(e) => setBill((b) => ({ ...b, amount: e.target.value }))} invalid={Boolean(billErr("amount"))} className="text-right font-mono tabular-nums" />
          </FormField>
          <FormField id="bill-due" label="Due date" error={billErr("due_date")}>
            <TextInput id="bill-due" type="date" value={bill.due_date} onChange={(e) => setBill((b) => ({ ...b, due_date: e.target.value }))} invalid={Boolean(billErr("due_date"))} />
          </FormField>
          <FormField id="bill-reference" label="Invoice number" error={billErr("reference")}>
            <TextInput id="bill-reference" value={bill.reference} onChange={(e) => setBill((b) => ({ ...b, reference: e.target.value }))} invalid={Boolean(billErr("reference"))} />
          </FormField>
          <FormField id="bill-note" label="Note" error={billErr("note")}>
            <TextInput id="bill-note" value={bill.note} onChange={(e) => setBill((b) => ({ ...b, note: e.target.value }))} invalid={Boolean(billErr("note"))} />
          </FormField>
        </div>
        <div className="flex justify-end">
          <Button type="submit" variant="primary" loading={addBill.pending}>
            Add bill
          </Button>
        </div>
      </form>

      {owes ? (
        <form onSubmit={onPay} noValidate aria-label="Record a payment" className="flex flex-col gap-3 rounded-card border-2 border-line-strong bg-surface-raised p-6 shadow-card">
          <h3 className="text-ui-base font-semibold text-fg">Record a payment</h3>
          {alert(payRefused)}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <FormField id="vendor-payment-amount" label="Amount paid (Rs)" required error={payErr("amount")}>
              <TextInput id="vendor-payment-amount" inputMode="decimal" value={payment.amount} onChange={(e) => setPayment((p) => ({ ...p, amount: e.target.value }))} invalid={Boolean(payErr("amount"))} className="text-right font-mono tabular-nums" />
            </FormField>
            <FormField id="vendor-payment-method" label="Paid by" required error={payErr("method")}>
              <SelectInput id="vendor-payment-method" value={payment.method} onChange={(e) => setPayment((p) => ({ ...p, method: e.target.value }))}>
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
        caption={`Payables ledger for ${vendor.name}`}
        columns={columns}
        rows={rows}
        state={ledger.state}
        rowKey={(r) => r.id}
        emptyMessage="No bills or payments yet."
        errorMessage={ledger.error?.message ?? "Could not load the ledger."}
        onRetry={ledger.reload}
      />
    </section>
  );
}
