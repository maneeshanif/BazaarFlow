import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { TapeStrip } from "@/components/brand/TapeStrip";

type Props = {
  children: ReactNode;
  /** degrees; negative leans left */
  tilt?: number;
  tape?: boolean;
  /** a second tape that slides onto the corner as the page scrolls */
  slide?: { x: number; y: number };
  className?: string;
};

const TILT: Record<number, string> = { [-8]: "-rotate-[8deg]", [-5]: "-rotate-[5deg]", [-3]: "-rotate-3", [0]: "", [3]: "rotate-3", [5]: "rotate-[5deg]", [8]: "rotate-[8deg]" };

/** A rounded photo frame, tilted, with a flat offset shadow and a tape strip on one corner. */
export function TiltFrame({ children, tilt = 3, tape = true, slide, className }: Props) {
  return (
    <div className={cn("relative", TILT[tilt] ?? "", className)}>
      {tape ? <TapeStrip className="-top-5 left-1/3 -translate-x-1/2 -rotate-3" /> : null}
      {slide ? <TapeStrip slide={slide} className="-top-4 right-[8%] h-14 w-48 rotate-[5deg]" /> : null}
      <div className="h-full w-full overflow-hidden rounded-card shadow-card">{children}</div>
    </div>
  );
}
