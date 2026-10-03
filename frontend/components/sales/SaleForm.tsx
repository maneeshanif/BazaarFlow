"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Button, buttonClass } from "@/components/app/Button";
import { Checkbox, SelectInput, TextArea, TextInput } from "@/components/form/Controls";
import { FormField } from "@/components/form/FormField";
import { FormShell } from "@/components/form/FormShell";
import { CustomerLookup, type CustomerChoice } from "@/components/sales/CustomerLookup";
import { ProductPicker } from "@/components/sales/ProductPicker";
import { useSubmit } from "@/hooks/useSubmit";
import { apiPost } from "@/lib/api/client";
import type { OrderDetail, Product, SalePreview } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatMoney } from "@/lib/format";
import { saleFormErrors, type SaleLineInput } from "@/lib/validation/sale";

type Line = { key: string; product: Product; qty: string; price: string };

const METHODS = [
  { value: "cash", label: "Cash" },
  { value: "card", label: "Card" },
  { value: "bank", label: "Bank transfer" },
  { value: "wallet", label: "Easypaisa or JazzCash" },
  { value: "udhaar", label: "On credit (udhaar)" },
];

const newKey = (): string => (typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : String(Math.random()));

const WHOLE = /^[1-9]\d{0,6}$/;
const MONEY = /^\d{1,12}(\.\d{1,2})?$/;

/**
 * New sale (PRD F-007) in the mandated transaction layout: master fields, line grid, totals, actions, audit.
 * The browser never adds up money: every total on screen comes from the preview endpoint, and the posted sale is
 * calculated again by the server. A retry of the same sale carries the same Idempotency-Key, so it posts once.
 */
export function SaleForm() {
  const router = useRouter();
  const { role } = useAuth();
  const canOverride = role === "owner" || role === "manager";
  const [lines, setLines] = useState<Line[]>([]);
  const [customer, setCustomer] = useState<CustomerChoice | null>(null);
  const [method, setMethod] = useState("cash");
  const [discount, setDiscount] = useState("");
  const [paid, setPaid] = useState("");
  const [note, setNote] = useState("");
  const [override, setOverride] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [posted, setPosted] = useState(false); // once posted the form is done: a second click must not make a second sale
  const idempotencyKey = useRef(newKey());

  const inputs: SaleLineInput[] = lines.map((l) => ({ qty: l.qty, price: l.price, name: l.product.name }));
  const problems = useMemo(
    () => saleFormErrors({ lines: inputs, discount, paid, method, hasCustomer: customer !== null }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [lines, discount, paid, method, customer],
  );

  // the server adds the sale up (debounced); the latest answer wins
  const [preview, setPreview] = useState<{ for: string; data?: SalePreview; error?: string } | null>(null);
  const request = useMemo(() => {
    const items = lines
      .filter((l) => WHOLE.test(l.qty))
      .map((l) => ({ product_id: l.product.id, qty: Number(l.qty), ...(MONEY.test(l.price) ? { unit_price: l.price } : {}) }));
    return {
      items,
      discount: MONEY.test(discount) ? discount : "0",
      payment_method: method,
      ...(method !== "udhaar" && MONEY.test(paid) ? { amount_paid: paid } : {}),
    };
  }, [lines, discount, method, paid]);
  const requestKey = JSON.stringify(request);
  useEffect(() => {
    let cancelled = false;
    const id = setTimeout(() => {
      apiPost<SalePreview>("/sales/preview", JSON.parse(requestKey))
        .then((data) => !cancelled && setPreview({ for: requestKey, data }))
        .catch((e: unknown) => !cancelled && setPreview({ for: requestKey, error: e instanceof Error ? e.message : "Could not add up the sale." }));
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(id);
    };
  }, [requestKey]);
  const current = preview?.for === requestKey ? preview : null;
  const totals = current?.data ?? preview?.data ?? null;
  const settling = lines.length > 0 && current === null;
  const shortOfStock = (totals?.lines ?? []).some((l) => !l.enough_stock);

  const post = useSubmit(() =>
    apiPost<OrderDetail>(
      "/sales/",
      {
        customer_id: customer?.id ?? null,
        items: request.items,
        discount: request.discount,
        payment_method: method,
        ...(method !== "udhaar" && MONEY.test(paid) ? { amount_paid: paid } : {}),
        note: note.trim() || null,
        stock_override: canOverride && override && shortOfStock,
      },
      { "Idempotency-Key": idempotencyKey.current },
    ),
  );

  function addProduct(product: Product) {
    setLines((current) => {
      const existing = current.find((l) => l.product.id === product.id);
      if (existing) return current.map((l) => (l === existing ? { ...l, qty: String(Number(l.qty || 0) + 1) } : l));
      return [...current, { key: newKey(), product, qty: "1", price: product.price }];
    });
  }
  const patch = (key: string, change: Partial<Line>) => setLines((c) => c.map((l) => (l.key === key ? { ...l, ...change } : l)));

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (posted) return;
    setSubmitted(true);
    if (Object.keys(allProblems).length > 0) return;
    const order = await post.run();
    if (!order) return;
    setPosted(true);
    toast.success(`Sale posted: ${formatMoney(order.total)}${order.amount_due !== "0.00" ? `, ${formatMoney(order.amount_due)} on credit` : ""}`);
    router.push(`/orders/${order.id}`);
  }

  const creditWithoutCustomer = customer === null && totals !== null && Number(totals.amount_due) > 0;
  const allProblems: Record<string, string> = creditWithoutCustomer
    ? { ...problems, customer: "Choose the customer: part of this sale is on credit, so we need to know who owes" }
    : problems;
  const show = (field: string): string | undefined => (submitted ? allProblems[field] : undefined);
  const refused = post.error?.message;
  const lineTotal = (key: string): string | null => {
    const l = lines.find((x) => x.key === key);
    return totals?.lines.find((t) => t.product_id === l?.product.id)?.line_total ?? null;
  };

  return (
    <form onSubmit={onSubmit} noValidate aria-label="New sale">
      <FormShell
        title="New sale"
        status="draft"
        filters={
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <CustomerLookup value={customer} onChange={setCustomer} error={show("customer")} />
            <FormField id="payment-method" label="Paid by" required>
              <SelectInput
                id="payment-method"
                value={method}
                onChange={(e) => {
                  setMethod(e.target.value);
                  if (e.target.value === "udhaar") setPaid("");
                }}
              >
                {METHODS.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </SelectInput>
            </FormField>
            <FormField
              id="amount-paid"
              label="Amount received (Rs)"
              error={show("paid")}
              hint={method === "udhaar" ? "Nothing is paid now; the whole total goes on their udhaar." : "Leave empty if they paid the full total. The rest goes on their udhaar."}
            >
              <TextInput
                id="amount-paid"
                inputMode="decimal"
                value={paid}
                disabled={method === "udhaar"}
                placeholder={totals && method !== "udhaar" ? totals.total : undefined}
                onChange={(e) => setPaid(e.target.value)}
                invalid={Boolean(show("paid"))}
                className="text-right font-mono tabular-nums"
              />
            </FormField>
            <FormField id="discount" label="Discount (Rs)" error={show("discount")}>
              <TextInput id="discount" inputMode="decimal" value={discount} onChange={(e) => setDiscount(e.target.value)} invalid={Boolean(show("discount"))} className="text-right font-mono tabular-nums" />
            </FormField>
            <FormField id="note" label="Note" className="md:col-span-2" error={show("note")}>
              <TextArea id="note" rows={2} maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />
            </FormField>
          </div>
        }
        totals={
          <dl aria-label="Sale totals" aria-busy={settling} className="ml-auto grid max-w-sm grid-cols-[1fr_auto] gap-x-6 gap-y-1 text-ui-base">
            <dt className="text-fg-muted">Items</dt>
            <dd className="text-right font-mono tabular-nums">{formatMoney(totals?.subtotal ?? 0)}</dd>
            <dt className="text-fg-muted">Discount</dt>
            <dd className="text-right font-mono tabular-nums">{formatMoney(totals?.discount ?? 0)}</dd>
            <dt className="text-ui-md font-semibold text-fg">Total</dt>
            <dd className="text-right font-mono text-ui-md font-semibold tabular-nums">{formatMoney(totals?.total ?? 0)}</dd>
            <dt className="text-fg-muted">Received now</dt>
            <dd className="text-right font-mono tabular-nums">{formatMoney(totals?.amount_paid ?? 0)}</dd>
            <dt className="text-fg-muted">On credit (udhaar)</dt>
            <dd className="text-right font-mono tabular-nums">{formatMoney(totals?.amount_due ?? 0)}</dd>
          </dl>
        }
        actions={
          <>
            <Link href="/dashboard" className={buttonClass("secondary")}>
              Cancel
            </Link>
            <Button type="submit" variant="primary" loading={post.pending} disabled={settling || posted}>
              Post sale
            </Button>
          </>
        }
        audit={<p>Posting a sale takes the stock out, records the payment and any udhaar, and writes an audit entry. A posted sale is changed only by reversing it.</p>}
      >
        {refused ? (
          <p role="alert" className="mb-3 rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
            {refused}
          </p>
        ) : null}
        {current?.error ? (
          <p role="alert" className="mb-3 rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-ui-sm text-danger">
            {current.error}
          </p>
        ) : null}
        {totals && totals.warnings.length > 0 ? (
          <ul role="status" className="mb-3 rounded-md border border-warning-border bg-warning-subtle px-3 py-2 text-ui-sm text-warning">
            {totals.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        ) : null}
        {canOverride && shortOfStock ? (
          <label className="mb-3 flex items-center gap-2 text-ui-base text-fg">
            <Checkbox checked={override} onChange={(e) => setOverride(e.target.checked)} />
            Sell more than the shelf count says (the count will be corrected and recorded)
          </label>
        ) : null}

        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-ui-md font-semibold text-fg">Items</h2>
          <ProductPicker onPick={addProduct} />
        </div>
        {show("lines") ? (
          <p role="alert" className="mb-2 text-ui-sm text-danger">
            {show("lines")}
          </p>
        ) : null}
        <div className="overflow-x-auto rounded-lg border border-border bg-surface">
          <table className="w-max min-w-full border-collapse">
            <caption className="sr-only">Items on this sale</caption>
            <thead>
              <tr className="bg-surface-sunken">
                {["Product", "In stock", "Quantity", "Price (Rs)", "Line total", ""].map((h, i) => (
                  <th key={`${h}-${i}`} scope="col" className={`px-3 py-2 text-ui-xs font-medium text-fg-muted ${i >= 1 && i <= 4 ? "text-right" : "text-left"}`}>
                    {h || <span className="sr-only">Remove</span>}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {lines.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-3 py-8 text-center text-ui-sm text-fg-muted">
                    No items yet. Use Add product to start the sale.
                  </td>
                </tr>
              ) : (
                lines.map((l, i) => {
                  const previewLine = totals?.lines.find((t) => t.product_id === l.product.id);
                  const lineError = show(`line-${i}`);
                  return (
                    <tr key={l.key} className="border-t border-border align-top">
                      <td className="px-3 py-2 text-ui-sm text-fg">
                        <div className="font-medium">{l.product.name}</div>
                        <div className="font-mono text-ui-xs text-fg-muted">{l.product.sku}</div>
                        {lineError ? (
                          <p role="alert" className="text-ui-xs text-danger">
                            {lineError}
                          </p>
                        ) : null}
                      </td>
                      <td className={`px-3 py-2 text-right font-mono text-ui-sm tabular-nums ${previewLine && !previewLine.enough_stock ? "text-danger" : "text-fg"}`}>{previewLine?.available ?? l.product.qty_on_hand}</td>
                      <td className="px-3 py-2">
                        <TextInput aria-label={`Quantity of ${l.product.name}`} inputMode="numeric" value={l.qty} onChange={(e) => patch(l.key, { qty: e.target.value })} invalid={Boolean(lineError)} className="w-24 text-right font-mono tabular-nums" />
                      </td>
                      <td className="px-3 py-2">
                        <TextInput aria-label={`Price of ${l.product.name}`} inputMode="decimal" value={l.price} onChange={(e) => patch(l.key, { price: e.target.value })} invalid={Boolean(lineError)} className="w-32 text-right font-mono tabular-nums" />
                      </td>
                      <td className="px-3 py-2 text-right font-mono text-ui-sm tabular-nums text-fg">{formatMoney(lineTotal(l.key))}</td>
                      <td className="px-3 py-2 text-right">
                        <Button variant="ghost" size="sm" onClick={() => setLines((c) => c.filter((x) => x.key !== l.key))} aria-label={`Remove ${l.product.name}`}>
                          Remove
                        </Button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </FormShell>
    </form>
  );
}
