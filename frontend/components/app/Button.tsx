"use client";

import { forwardRef, type ButtonHTMLAttributes } from "react";
import { useT } from "@/lib/i18n/LocaleProvider";
import { cn } from "@/lib/utils";

/**
 * The one button (ui-rules.md "Buttons"): primary for the single main action, secondary for supporting actions,
 * ghost for tertiary/toolbar, danger for confirmed destructive actions. Heights come from the control tokens.
 */
export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

const variants: Record<ButtonVariant, string> = {
  primary: "bg-action text-fg-inverse shadow-card hover:bg-action-hover active:translate-y-0.5 active:bg-action-active active:shadow-none",
  secondary: "border-2 border-action bg-surface text-fg hover:bg-lime hover:text-forest-ink",
  ghost: "text-fg hover:bg-surface-hover",
  danger: "bg-danger text-fg-inverse shadow-card hover:bg-danger-hover active:translate-y-0.5 active:shadow-none",
};

const sizes: Record<ButtonSize, string> = {
  sm: "h-control-sm px-4 text-ui-sm",
  md: "h-control-md px-5 text-ui-base",
  lg: "h-control-lg px-7 text-ui-md",
};

/** Class names for anything that must look like a button, e.g. a Link. */
export function buttonClass(variant: ButtonVariant = "secondary", size: ButtonSize = "md", className?: string): string {
  return cn(
    "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-pill font-bold transition-all duration-200",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-focus",
    "aria-disabled:cursor-not-allowed aria-disabled:opacity-60 disabled:cursor-not-allowed disabled:opacity-60",
    variants[variant],
    sizes[size],
    className,
  );
}

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** a request is in flight: the button is disabled and announces it, so it cannot be pressed twice */
  loading?: boolean;
};

export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { variant = "secondary", size = "md", loading = false, disabled, className, children, type = "button", ...rest },
  ref,
) {
  const t = useT();
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={buttonClass(variant, size, className)}
      {...rest}
    >
      {typeof children === "string" ? t(children) : children}
    </button>
  );
});
