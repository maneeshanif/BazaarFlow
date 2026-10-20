"use client";

import type { ReactNode } from "react";
import { useT } from "@/lib/i18n/LocaleProvider";

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  const t = useT();
  return (
    <div className="seam-arc mb-6 flex flex-wrap items-center justify-between gap-4 bg-lime px-6 pb-10 pt-6 text-forest-ink dark:bg-surface-raised dark:text-lime md:px-8">
      <div className="min-w-0">
        <h1 className="text-ui-3xl md:text-display-lg">{t(title)}</h1>
        {description ? <p className="mt-1 max-w-prose text-ui-base font-medium">{t(description)}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
    </div>
  );
}
