"use client";

import type { ReactNode } from "react";
import { useT } from "@/lib/i18n/LocaleProvider";

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  const t = useT();
  return (
    <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
      <div className="min-w-0">
        <h1 className="text-ui-lg font-semibold text-fg">{t(title)}</h1>
        {description ? <p className="text-ui-sm text-fg-muted">{t(description)}</p> : null}
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </div>
  );
}
