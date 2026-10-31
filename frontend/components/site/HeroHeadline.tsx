"use client";

import { useRef } from "react";
import { CutWord } from "@/components/site/CutTitle";
import { PROXIMITY_HEADING, useProximity } from "@/components/site/text";
import { BrandImage } from "@/components/brand/BrandImage";

/**
 * The hero headline: a small line with the logo badge in the middle, then two lines of very large hand-cut capitals. The
 * whole sentence is exposed once to assistive technology. The letters drop in after the opening has cleared, and the
 * big lines lean away from the pointer a little as it moves over the hero (the reference does the same).
 */
export function HeroHeadline() {
  const lean = useRef<HTMLDivElement | null>(null);
  useProximity(lean, { ...PROXIMITY_HEADING, radius: 2.1, lift: 0.06 });
  return (
    <div ref={lean}>
      <h1 className="text-center font-display uppercase text-forest-ink">
        <span className="sr-only">Tell it what you sold. It keeps the khata.</span>
        <span aria-hidden className="block">
          <span className="hero-small flex items-center justify-center gap-3 md:gap-6">
            <span>Tell it</span>
            <span className="inline-block h-[2em] w-[3.8em] shrink-0 -rotate-6 overflow-hidden rounded-chip">
              <BrandImage file="logo-badge.png" alt="" decorative label="BazaarFlow" tone="forest" />
            </span>
            <span>what you sold.</span>
          </span>
          <span className="mt-2 block md:mt-4">
            <span className="hero-giant block">
              <CutWord text="It keeps" from={0} />
            </span>
            <span className="hero-giant block">
              <CutWord text="the khata" from={8} />
            </span>
          </span>
        </span>
      </h1>
    </div>
  );
}
