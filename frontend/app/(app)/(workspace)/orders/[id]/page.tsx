"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Button, buttonClass } from "@/components/app/Button";
import { DataTable, type Column } from "@/components/app/DataTable";
import { ErrorState, UnauthorizedState } from "@/components/app/StateViews";
import { FormShell } from "@/components/form/FormShell";
import { ReverseDialog } from "@/components/orders/ReverseDialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useLoad } from "@/hooks/useLoad";
import { apiGet } from "@/lib/api/client";
import type { OrderDetail } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatDateTime, formatMoney } from "@/lib/format";

type ItemRow = OrderDetail["items"][number];
type PaymentRow = OrderDetail["payments"][number] & { when: string };

/** One order (PRD F-008). A posted sale has no Edit or Delete: managers can reverse it, everything else is read-only. */
export default function OrderPage() {
  const { id } = useParams<{ id: string }>();
  const { role } = useAuth();
  const canReverse = role === "owner" || role === "manager";
  const [override, setOverride] = useState<OrderDetail | null>(null);
  const [reversing, setReversing] = useState(false);
  const loaded = useLoad(() => apiGet<OrderDetail>(`/orders/${id}`), [id]);

  if (loaded.state === "loading") {
    return (
      <div role="status" aria-busy="true" aria-label="Loading order" className="flex flex-col gap-3">
        <Skeleton className="h-6 w-56" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }
  if (loaded.state === "unauthorized") return <UnauthorizedState />;
  if (loaded.state === "error" || !loaded.data) {
    const notFound = loaded.error?.status === 404;
    return <ErrorState message={notFound ? "That order does not exist." : (loaded.error?.message ?? "Could not load this order.")} onRetry={notFound ? undefined : loaded.reload} />;
  }

  const order = override ?? loaded.data;
  const showCost = order.items.some((i) => i.unit_cost !== null);
  const itemColumns: Column<ItemRow>[] = [
    { key: "product_name", header: "Product" },
    { key: "qty", header: "Quantity", numeric: true },
    { key: "unit_price", header: "Price", money: true },
    ...(showCost ? ([{ key: "unit_cost", header: "Cost", money: true }] as Column<ItemRow>[]) : []),
    { key: "line_total", header: "Line total", money: true },
  ];
  const paymentRows: PaymentRow[] = order.payments.map((p) => ({ ...p, when: formatDateTime(p.created_at) }));
  const paymentColumns: Column<PaymentRow>[] = [
    { key: "when", header: "When" },
    { key: "method", header: "Paid by" },
    { key: "amount", header: "Amount", money: true },
    { key: "status", header: "Status", status: true },
  ];
  const ref = order.id.slice(0, 8).toUpperCase();

  return (
    <>
      <FormShell
        title={`Order ${ref}`}
        status={order.status}
        filters={
          <dl className="grid grid-cols-1 gap-x-8 gap-y-2 text-ui-base md:grid-cols-2">
            <div>
              <dt className="text-ui-xs font-medium text-fg-muted">Customer</dt>
              <dd className="text-fg">
                {order.customer_id && canReverse ? (
                  <Link href={`/customers/${order.customer_id}`} className="font-medium text-action hover:underline">
                    {order.customer_name}
                  </Link>
                ) : (
                  (order.customer_name ?? "Walk-in")
                )}
              </dd>
            </div>
            <div>
              <dt className="text-ui-xs font-medium text-fg-muted">When</dt>
              <dd className="text-fg">{formatDateTime(order.created_at)}</dd>
            </div>
            <div>
              <dt className="text-ui-xs font-medium text-fg-muted">Channel</dt>
              <dd className="text-fg">{order.channel === "pos" ? "Point of sale" : order.channel}</dd>
            </div>
            {order.note ? (
              <div className="md:col-span-2">
                <dt className="text-ui-xs font-medium text-fg-muted">Note</dt>
                <dd className="whitespace-pre-line text-fg">{order.note}</dd>
              </div>
            ) : null}
          </dl>
        }
        totals={
          <dl aria-label="Order totals" className="ml-auto grid max-w-sm grid-cols-[1fr_auto] gap-x-6 gap-y-1 text-ui-base">
            <dt className="text-fg-muted">Items</dt>
            <dd className="text-right font-mono tabular-nums">{formatMoney(order.subtotal)}</dd>
            <dt className="text-fg-muted">Discount</dt>
            <dd className="text-right font-mono tabular-nums">{formatMoney(order.discount)}</dd>
            <dt className="text-ui-md font-semibold text-fg">Total</dt>
            <dd className="text-right font-mono text-ui-md font-semibold tabular-nums">{formatMoney(order.total)}</dd>
            <dt className="text-fg-muted">Received</dt>
            <dd className="text-right font-mono tabular-nums">{formatMoney(order.amount_paid)}</dd>
            <dt className="text-fg-muted">Still owed (udhaar)</dt>
            <dd className="text-right font-mono tabular-nums">{formatMoney(order.amount_due)}</dd>
          </dl>
        }
        actions={
          <>
            <Link href="/orders" className={buttonClass("secondary")}>
              Back to orders
            </Link>
            {canReverse && order.status === "posted" ? (
              <Button variant="danger" onClick={() => setReversing(true)}>
                Reverse sale
              </Button>
            ) : null}
          </>
        }
        audit={
          <p>
            Posted {formatDateTime(order.created_at)}. Last changed {formatDateTime(order.updated_at)}. A posted sale is never edited or deleted; reversing it keeps both
            records in the audit log.
          </p>
        }
      >
        <div className="flex flex-col gap-4">
          <section aria-label="Items">
            <h2 className="mb-2 text-ui-md font-semibold text-fg">Items</h2>
            <DataTable caption="Items on this order" columns={itemColumns} rows={order.items} state={order.items.length ? "ready" : "empty"} rowKey={(r) => r.id} emptyMessage="This order has no item lines (it was imported)." />
          </section>
          <section aria-label="Payments">
            <h2 className="mb-2 text-ui-md font-semibold text-fg">Payments</h2>
            <DataTable caption="Payments on this order" columns={paymentColumns} rows={paymentRows} state={paymentRows.length ? "ready" : "empty"} rowKey={(r) => r.id} emptyMessage="Nothing was paid on this order; it all went on credit." />
          </section>
        </div>
      </FormShell>
      {canReverse && order.status === "posted" ? (
        <ReverseDialog
          order={order}
          open={reversing}
          onOpenChange={setReversing}
          onReversed={(done) => {
            setOverride(done);
            toast.success(`Order ${ref} reversed. The stock is back on the shelf.`);
          }}
        />
      ) : null}
    </>
  );
}
