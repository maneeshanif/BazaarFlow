import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { TapeStrip } from "@/components/brand/TapeStrip";

type Props = {
  children: ReactNode;
  /** degrees; negative leans left */
  tilt?: number;
  tape?: boolean;
  className?: string;
};

const TILT: Record<number, string> = { [-8]: "-rotate-[8deg]", [-5]: "-rotate-[5deg]", [-3]: "-rotate-3", [0]: "", [3]: "rotate-3", [5]: "rotate-[5deg]", [8]: "rotate-[8deg]" };

/** A rounded photo frame, tilted, with a flat offset shadow and a tape strip on one corner. */
export function TiltFrame({ children, tilt = 3, tape = true, className }: Props) {
  return (
    <div className={cn("relative", TILT[tilt] ?? "", className)}>
      {tape ? <TapeStrip className="-top-3 left-1/2 -translate-x-1/2 -rotate-3" /> : null}
      <div className="h-full w-full overflow-hidden rounded-card shadow-card">{children}</div>
    </div>
  );
}
