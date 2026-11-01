"use client";

import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useLayoutEffect, useRef } from "react";
import { cn } from "@/lib/utils";

let registered = false;

/**
 * A translucent kraft tape strip across a corner. Drawn in CSS so it works before any artwork exists. When motion is
 * allowed the strip is pulled out from one end as it scrolls into view, then stays; otherwise it is simply there.
 */
export function TapeStrip({ className, slide }: { className?: string; slide?: { x: number; y: number } }) {
  const ref = useRef<HTMLSpanElement | null>(null);
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
    <span
      ref={ref}
      aria-hidden
      className={cn("pointer-events-none absolute z-10 block h-12 w-40 rounded-[2px] bg-kraft/70 shadow-popover [clip-path:polygon(2%_0,98%_6%,100%_90%,3%_100%,0_55%)]", className)}
    />
  );
}
