import Link from "next/link";
import { cn } from "@/lib/utils";

type Props = {
  label: string;
  value: string;
  /** e.g. "+8%" ; the sign decides the tone */
  delta?: string;
  /** every KPI drills down to the records behind it (ui-rules.md "Dashboards") */
  href: string;
};

export function KpiCard({ label, value, delta, href }: Props) {
  const tone = delta?.startsWith("-") ? "text-negative" : "text-positive";
  return (
    <Link
      href={href}
      className="flex min-w-0 flex-col gap-1 rounded-lg border border-border bg-surface p-4 hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-focus"
    >
      <span className="text-ui-xs text-fg-muted">{label}</span>
      <span className="truncate font-mono text-ui-xl font-semibold tabular-nums text-fg">{value}</span>
      {delta ? <span className={cn("text-ui-xs font-medium", tone)}>{delta} vs last period</span> : null}
    </Link>
  );
}
