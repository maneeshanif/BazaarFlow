import { forwardRef, type InputHTMLAttributes, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

/**
 * Form controls built on the control tokens (ui-rules.md "Forms & Validation"): 34px default height, visible focus
 * ring, and `invalid` switches the border to the danger token. Pair each with a FormField for label and message.
 */
const base =
  "w-full rounded-md border bg-surface px-3 text-ui-base text-fg placeholder:text-fg-subtle " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-focus " +
  "disabled:cursor-not-allowed disabled:text-fg-subtle read-only:bg-surface-sunken";

const edge = (invalid?: boolean) => (invalid ? "border-danger" : "border-border");

type WithInvalid<T> = T & { invalid?: boolean };

export const TextInput = forwardRef<HTMLInputElement, WithInvalid<InputHTMLAttributes<HTMLInputElement>>>(function TextInput(
  { invalid, className, ...rest },
  ref,
) {
  return <input ref={ref} aria-invalid={invalid || undefined} className={cn(base, "h-control-md", edge(invalid), className)} {...rest} />;
});

export const SelectInput = forwardRef<HTMLSelectElement, WithInvalid<SelectHTMLAttributes<HTMLSelectElement>>>(function SelectInput(
  { invalid, className, children, ...rest },
  ref,
) {
  return (
    <select ref={ref} aria-invalid={invalid || undefined} className={cn(base, "h-control-md", edge(invalid), className)} {...rest}>
      {children}
    </select>
  );
});

export const TextArea = forwardRef<HTMLTextAreaElement, WithInvalid<TextareaHTMLAttributes<HTMLTextAreaElement>>>(function TextArea(
  { invalid, className, ...rest },
  ref,
) {
  return <textarea ref={ref} aria-invalid={invalid || undefined} className={cn(base, "min-h-20 py-2", edge(invalid), className)} {...rest} />;
});

export const Checkbox = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Checkbox({ className, ...rest }, ref) {
  return (
    <input
      ref={ref}
      type="checkbox"
      className={cn(
        "h-4 w-4 rounded-sm border border-line-strong accent-action",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-focus",
        className,
      )}
      {...rest}
    />
  );
});
