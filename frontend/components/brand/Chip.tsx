import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** The small tag with a grip glyph ("NEWS", "HIGHLIGHT") used above headings and on cards. */
export function Chip({ children, tone = "forest", className }: { children: ReactNode; tone?: "forest" | "tan"; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-chip px-3 py-1 font-display text-ui-sm uppercase tracking-wide",
        tone === "forest" ? "bg-forest text-lime" : "bg-cream-tan text-forest-ink",
        className,
      )}
    >
      <span aria-hidden className="text-ui-xs leading-none">
        &#8942;
      </span>
      {children}
    </span>
  );
}
