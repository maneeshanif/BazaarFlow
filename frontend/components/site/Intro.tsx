"use client";

import { useEffect } from "react";
import { BrandImage } from "@/components/brand/BrandImage";
import { INTRO_TOTAL_SECONDS, markIntroSeen } from "@/components/site/intro-state";

/**
 * Layers, top first. The lime one carries the logo and lifts away first; the colours behind it follow, each a little
 * later, so the page seems to be uncovered by a rainbow of curved sheets (measured on the reference, home-motion-measured.md).
 */
const LAYERS = ["bg-lime", "bg-coral", "bg-orange", "bg-sunny", "bg-lime", "bg-sky", "bg-indigo"];
const HOLD = 1.75; // seconds the logo is on screen before the first layer lifts

/**
 * The first-visit opening: a lime screen, the logo badge pops in, then curved coloured sheets lift off the top and the hero
 * is underneath. Once per browser session, never for reduced motion, never takes pointer input, hidden from assistive
 * technology, and it hides itself (CSS) when it is done.
 */
export function Intro() {
  useEffect(() => {
    const root = document.documentElement;
    if (!root.dataset.intro) return;
    markIntroSeen();
    // when it is over, drop the flag so later pages in this visit do not wait for an opening that is not there
    const timer = window.setTimeout(() => delete root.dataset.intro, INTRO_TOTAL_SECONDS * 1000 + 200);
    return () => window.clearTimeout(timer);
  }, []);
  return (
    <div aria-hidden data-testid="intro" className="intro-root pointer-events-none fixed inset-0 z-[150]" style={{ animation: `intro-gone 0s ${INTRO_TOTAL_SECONDS}s forwards` }}>
      {LAYERS.map((tone, i) => (
        <div
          key={i}
          className={`absolute inset-0 ${tone} flex items-center justify-center rounded-b-[50%_14vh]`}
          style={{ zIndex: LAYERS.length - i, animation: `arc-leave 0.95s ${HOLD + i * 0.07}s cubic-bezier(0.7,0,0.3,1) forwards` }}
        >
          {i === 0 ? (
            <div className="h-28 w-44 overflow-hidden rounded-chip" style={{ animation: "sticker-drop 1.25s 0.2s linear both", transformOrigin: "50% 100%" }}>
              <BrandImage file="logo-badge.png" alt="" decorative label="BazaarFlow" tone="forest" />
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
