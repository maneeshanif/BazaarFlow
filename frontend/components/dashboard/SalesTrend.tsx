import Link from "next/link";
import { cn } from "@/lib/utils";
import { buttonClass } from "@/components/app/Button";
import type { Dashboard } from "@/lib/api/types";
import { formatMoney } from "@/lib/format";

/** One identity colour per day, from the chart tokens. */
const BAR = ["bg-ui-chart-1", "bg-ui-chart-2", "bg-ui-chart-3", "bg-ui-chart-4", "bg-ui-chart-5", "bg-ui-chart-6", "bg-ui-chart-1"];

const WEEKDAY = new Intl.DateTimeFormat("en-GB", { weekday: "short", timeZone: "UTC" });

/**
 * Sales for the last 7 days as bars (PRD §8: bar charts compare). The bar heights are only drawing: every figure is
 * from the server and is also in the table for screen readers. With no sales it says what to do instead of an empty plot.
 */
export function SalesTrend({ trend }: { trend: Dashboard["trend"] }) {
  const max = Math.max(...trend.map((d) => Number(d.total)), 0);
  if (max === 0) {
    return (
      <section aria-label="Sales, last 7 days" className="flex flex-col items-start gap-3 rounded-card border-2 border-line-strong bg-surface-raised p-6 shadow-card">
        <h2 className="text-ui-md font-semibold text-fg">Sales, last 7 days</h2>
        <p className="text-ui-sm text-fg-muted">No sales in the last 7 days. Record your first sale and the week will fill in here.</p>
        <Link href="/sales/new" className={buttonClass("primary")}>
          New sale
        </Link>
      </section>
    );
  }
  return (
    <section aria-label="Sales, last 7 days" className="rounded-card border-2 border-line-strong bg-surface-raised p-6 shadow-card">
      <h2 className="text-ui-md font-semibold text-fg">Sales, last 7 days</h2>
      <div className="mt-6 flex h-56 items-end gap-3" aria-hidden="true">
        {trend.map((d, i) => (
          <div key={d.day} className="flex h-full min-w-0 flex-1 flex-col justify-end gap-1">
            <div className={cn("rounded-t-chip", BAR[i % BAR.length])} style={{ height: `${Math.max((Number(d.total) / max) * 100, d.orders > 0 ? 3 : 0)}%` }} title={`${d.day}: ${formatMoney(d.total)}`} />
            <span className="text-center font-display text-ui-sm uppercase text-fg-muted">{WEEKDAY.format(new Date(`${d.day}T00:00:00Z`))}</span>
          </div>
        ))}
      </div>
      <table className="sr-only">
        <caption>Sales per day, last 7 days</caption>
        <thead>
          <tr>
            <th scope="col">Day</th>
            <th scope="col">Sales</th>
            <th scope="col">Orders</th>
          </tr>
        </thead>
        <tbody>
          {trend.map((d) => (
            <tr key={d.day}>
              <th scope="row">{d.day}</th>
              <td>{formatMoney(d.total)}</td>
              <td>{d.orders}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
