"use client";

import { useEffect, useSyncExternalStore } from "react";
import { BrandImage } from "@/components/brand/BrandImage";
import { introWillPlay, markIntroSeen } from "@/components/site/intro-state";

/**
 * Layers, top first. The lime one carries the logo and lifts away first; the colours behind it follow, each a little
 * later, so the page seems to be uncovered by a rainbow of curved sheets (measured on the reference, home-motion-measured.md).
 */
const LAYERS = ["bg-lime", "bg-coral", "bg-orange", "bg-sunny", "bg-lime", "bg-sky", "bg-indigo"];
const HOLD = 1.45; // seconds the logo is on screen before the first layer lifts

/**
 * The first-visit opening: a lime screen, the logo badge pops in, then curved coloured sheets lift off the top and the hero
 * is underneath. Once per browser session, never for reduced motion, never takes pointer input, hidden from assistive
 * technology, and it hides itself (CSS) when it is done.
 */
export function Intro() {
  const show = useSyncExternalStore(
    () => () => {},
    introWillPlay,
    () => false,
  );
  useEffect(() => {
    if (show) markIntroSeen();
  }, [show]);
  if (!show) return null;
  return (
    <div
      aria-hidden
      data-testid="intro"
      className="pointer-events-none fixed inset-0 z-[150]"
      style={{ animation: `intro-gone 0s ${HOLD + 1.4}s forwards` }}
    >
      {LAYERS.map((tone, i) => (
        <div
          key={i}
          className={`absolute inset-0 ${tone} flex items-center justify-center rounded-b-[50%_14vh]`}
          style={{ zIndex: LAYERS.length - i, animation: `arc-leave 0.95s ${HOLD + i * 0.07}s cubic-bezier(0.7,0,0.3,1) forwards` }}
        >
          {i === 0 ? (
            <div className="h-28 w-44 overflow-hidden rounded-chip" style={{ animation: "logo-pop 0.7s 0.25s var(--ease-bounce) both" }}>
              <BrandImage file="logo-badge.png" alt="" decorative label="BazaarFlow" tone="forest" />
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
