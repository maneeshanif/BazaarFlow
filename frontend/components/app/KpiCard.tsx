"use client";

import Link from "next/link";
import { RoundArrow } from "@/components/brand/RoundArrow";
import { useT } from "@/lib/i18n/LocaleProvider";
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
  const t = useT();
  const tone = delta?.startsWith("-") ? "text-negative" : "text-positive";
  return (
    <Link
      href={href}
      className="tilt-hover relative flex min-w-0 flex-col gap-2 rounded-card border-2 border-line-strong bg-surface-raised p-6 shadow-card focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-line-focus"
    >
      <span className="flex items-start justify-between gap-2">
        <span className="font-display text-ui-base uppercase tracking-wide text-fg-muted">{t(label)}</span>
        <RoundArrow />
      </span>
      <span className="truncate font-display text-ui-3xl tabular-nums text-fg">{value}</span>
      {delta ? <span className={cn("text-ui-sm font-bold", tone)}>{delta} vs last period</span> : null}
    </Link>
  );
}
