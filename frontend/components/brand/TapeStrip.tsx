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
export function TapeStrip({ className }: { className?: string }) {
  const ref = useRef<HTMLSpanElement | null>(null);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (!registered) {
      gsap.registerPlugin(ScrollTrigger);
      registered = true;
    }
    const ctx = gsap.context(() => {
      gsap.fromTo(
        el,
        { clipPath: "inset(0 100% 0 0)", xPercent: -30, opacity: 0.6 },
        { clipPath: "inset(0 0% 0 0)", xPercent: 0, opacity: 1, duration: 0.8, ease: "power3.out", clearProps: "clipPath", scrollTrigger: { trigger: el, start: "top 92%", once: true } },
      );
    });
    return () => ctx.revert();
  }, []);
  return (
    <span
      ref={ref}
      aria-hidden
      className={cn("pointer-events-none absolute z-10 block h-8 w-24 rounded-[2px] bg-kraft/70 shadow-popover [clip-path:polygon(2%_0,98%_6%,100%_90%,3%_100%,0_55%)]", className)}
    />
  );
}
