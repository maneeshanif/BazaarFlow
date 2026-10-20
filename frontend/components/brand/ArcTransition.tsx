"use client";

import { usePathname } from "next/navigation";
import { useState, useSyncExternalStore } from "react";

/** Stacked arcs, outermost first: coral, orange, sunny, lime, sky, indigo (identity colours, all tokens). */
const ARCS = ["bg-coral", "bg-orange", "bg-sunny", "bg-lime", "bg-sky", "bg-indigo"];

const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * The signature page-change moment: coloured arcs sweep up the screen and away (ADR 0005). Pure decoration, so it is
 * hidden from assistive technology, never takes pointer input, and is not drawn for people who prefer reduced motion.
 * It renders nothing on the first page; each later route change remounts it (keyed by the path), which replays the
 * CSS animation, and the arcs end off-screen.
 */
export function ArcTransition() {
  const pathname = usePathname();
  const [firstPath] = useState(pathname);
  const reduced = useSyncExternalStore(
    () => () => {},
    reducedMotion,
    () => true,
  );
  if (reduced || pathname === firstPath) return null;
  return (
    <div key={pathname} aria-hidden data-testid="arc-transition" className="pointer-events-none fixed inset-0 z-[60] overflow-hidden">
      {ARCS.map((tone, i) => (
        <div
          key={tone}
          className={`absolute inset-x-[-25%] top-0 h-[130%] rounded-[50%] ${tone}`}
          style={{ animation: `arc-rise 0.55s ${i * 0.07}s cubic-bezier(0.7,0,0.3,1) both, arc-leave 0.5s ${0.75 + i * 0.05}s cubic-bezier(0.7,0,0.3,1) forwards` }}
        />
      ))}
    </div>
  );
}
