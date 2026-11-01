"use client";

import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useLayoutEffect, useRef } from "react";
import { cn } from "@/lib/utils";

let registered = false;

const FACE = "url(/brand/tape-masking.png)";

/**
 * A strip of real masking tape (a photograph) across a corner. It is made of two halves meeting in the middle. At first only
 * one half is stuck down and the other stands up off the surface; as the page scrolls the loose half folds down and sticks,
 * and scrolling back lifts it again (the reference does the same). With reduced motion the whole strip is simply stuck.
 */
export function TapeStrip({ className }: { className?: string }) {
  const ref = useRef<HTMLSpanElement | null>(null);
  const loose = useRef<HTMLSpanElement | null>(null);
  useLayoutEffect(() => {
    const el = ref.current;
    const half = loose.current;
    if (!el || !half || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (!registered) {
      gsap.registerPlugin(ScrollTrigger);
      registered = true;
    }
    const ctx = gsap.context(() => {
      gsap.fromTo(
        half,
        { rotateY: -115, filter: "brightness(1.18)" },
        { rotateY: 0, filter: "brightness(1)", ease: "power1.inOut", scrollTrigger: { trigger: el.parentElement, start: "top 88%", end: "top 40%", scrub: 0.6 } },
      );
    });
    return () => ctx.revert();
  }, []);
  return (
    <span
      ref={ref}
      aria-hidden
      className={cn("pointer-events-none absolute z-10 block h-12 w-40 [perspective:700px] drop-shadow-[0_2px_2px_color-mix(in_srgb,var(--color-forest-ink)_35%,transparent)]", className)}
    >
      <span className="absolute inset-y-0 left-0 w-1/2 bg-no-repeat" style={{ backgroundImage: FACE, backgroundSize: "200% 100%", backgroundPosition: "0 0" }} />
      <span ref={loose} className="absolute inset-y-0 right-0 w-1/2 origin-left bg-no-repeat" style={{ backgroundImage: FACE, backgroundSize: "200% 100%", backgroundPosition: "100% 0" }} />
    </span>
  );
}
