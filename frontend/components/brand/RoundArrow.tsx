import { ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";

/** The round lime up-right arrow that sits on cards that open something. Decorative: the card itself is the link. */
export function RoundArrow({ className }: { className?: string }) {
  return (
    <span aria-hidden className={cn("inline-flex h-9 w-9 items-center justify-center rounded-full bg-lime text-forest-ink", className)}>
      <ArrowUpRight className="h-4 w-4" />
    </span>
  );
}
