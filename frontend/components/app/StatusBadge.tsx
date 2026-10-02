import { cn } from "@/lib/utils";
import { labelFor, toneFor, type Tone } from "@/lib/status";

const TONE_CLASS: Record<Tone, string> = {
  success: "bg-success-subtle text-success border-success-border",
  warning: "bg-warning-subtle text-warning border-warning-border",
  danger: "bg-danger-subtle text-danger border-danger-border",
  info: "bg-info-subtle text-info border-info-border",
  neutral: "bg-neutral-subtle text-neutral border-neutral-border",
  accent: "bg-action-subtle text-action border-action-border",
};

/**
 * Status as a badge. It always carries text (never colour alone) and the tone comes from lib/status so a status
 * looks the same on every screen.
 */
export function StatusBadge({ status, label, className }: { status: string; label?: string; className?: string }) {
  const tone = toneFor(status);
  return (
    <span
      data-tone={tone}
      className={cn(
        "inline-flex items-center rounded-sm border px-2 py-0.5 text-ui-2xs font-medium leading-4",
        TONE_CLASS[tone],
        className,
      )}
    >
      {label ?? labelFor(status)}
    </span>
  );
}
