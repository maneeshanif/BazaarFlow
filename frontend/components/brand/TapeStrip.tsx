"use client";

import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useLayoutEffect, useRef } from "react";
import { cn } from "@/lib/utils";

let registered = false;

/**
 * A strip of real masking tape (a photograph) across a corner. When motion is
 * allowed the strip is pulled out from one end as it scrolls into view, then stays; otherwise it is simply there.
 */
export function TapeStrip({ className, slide }: { className?: string; slide?: { x: number; y: number } }) {
  const ref = useRef<HTMLImageElement | null>(null);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (!registered) {
      gsap.registerPlugin(ScrollTrigger);
      registered = true;
    }
    const ctx = gsap.context(() => {
      if (slide) {
        // the reference's loose tape: it travels diagonally onto the card as you scroll down and lifts off again as you scroll up
        gsap.fromTo(el, { x: slide.x, y: slide.y, rotate: -10 }, { x: 0, y: 0, rotate: 0, ease: "none", scrollTrigger: { trigger: el.parentElement, start: "top 92%", end: "top 38%", scrub: 0.6 } });
        return;
      }
      gsap.fromTo(
        el,
        { clipPath: "inset(0 100% 0 0)", xPercent: -30, opacity: 0.6 },
        { clipPath: "inset(0 0% 0 0)", xPercent: 0, opacity: 1, duration: 0.8, ease: "power3.out", clearProps: "clipPath", scrollTrigger: { trigger: el, start: "top 92%", once: true } },
      );
    });
    return () => ctx.revert();
  }, [slide]);
  return (
    // eslint-disable-next-line @next/next/no-img-element -- a small decorative strip; the file is local and has fixed proportions
    <img
      ref={ref}
      src="/brand/tape-masking.png"
      alt=""
      aria-hidden
      draggable={false}
      className={cn("pointer-events-none absolute z-10 block h-12 w-40 select-none object-fill opacity-95 drop-shadow-[0_2px_2px_color-mix(in_srgb,var(--color-forest-ink)_35%,transparent)]", className)}
    />
  );
}
