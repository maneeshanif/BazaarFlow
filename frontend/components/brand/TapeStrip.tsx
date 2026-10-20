import { cn } from "@/lib/utils";

/** A translucent kraft tape strip across a corner. Drawn in CSS so it works before any artwork exists. */
export function TapeStrip({ className }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={cn("pointer-events-none absolute z-10 block h-8 w-24 rounded-[2px] bg-kraft/70 shadow-popover [clip-path:polygon(2%_0,98%_6%,100%_90%,3%_100%,0_55%)]", className)}
    />
  );
}
