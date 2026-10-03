import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

/**
 * The one button (ui-rules.md "Buttons"): primary for the single main action, secondary for supporting actions,
 * ghost for tertiary/toolbar, danger for confirmed destructive actions. Heights come from the control tokens.
 */
export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

const variants: Record<ButtonVariant, string> = {
  primary: "bg-action text-fg-inverse hover:bg-action-hover active:bg-action-active",
  secondary: "border border-border bg-surface text-fg hover:bg-surface-hover",
  ghost: "text-fg-muted hover:bg-surface-hover hover:text-fg",
  danger: "bg-danger text-fg-inverse hover:bg-danger-hover",
};

const sizes: Record<ButtonSize, string> = {
  sm: "h-control-sm px-2 text-ui-sm",
  md: "h-control-md px-3 text-ui-base",
  lg: "h-control-lg px-4 text-ui-base",
};

/** Class names for anything that must look like a button, e.g. a Link. */
export function buttonClass(variant: ButtonVariant = "secondary", size: ButtonSize = "md", className?: string): string {
  return cn(
    "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md font-medium transition-colors",
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
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={buttonClass(variant, size, className)}
      {...rest}
    >
      {children}
    </button>
  );
});
