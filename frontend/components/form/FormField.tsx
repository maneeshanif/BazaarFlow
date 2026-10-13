"use client";

import type { ReactNode } from "react";
import { useT } from "@/lib/i18n/LocaleProvider";
import { cn } from "@/lib/utils";

type Props = {
  id: string;
  label: string;
  required?: boolean;
  /** inline validation message, directly below the field */
  error?: string;
  hint?: string;
  children: ReactNode;
  className?: string;
};

/** Label above the control, required marker, inline error below (ui-rules.md "Forms & Validation"). */
export function FormField({ id, label, required, error, hint, children, className }: Props) {
  const t = useT();
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <label htmlFor={id} className="text-ui-xs font-medium text-fg-muted">
        {t(label)}
        {required ? (
          <span aria-hidden className="text-danger">
            {" "}
            *
          </span>
        ) : null}
      </label>
      <div aria-describedby={describedBy}>{children}</div>
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-ui-xs text-danger">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-ui-xs text-fg-subtle">
          {t(hint)}
        </p>
      ) : null}
    </div>
  );
}
