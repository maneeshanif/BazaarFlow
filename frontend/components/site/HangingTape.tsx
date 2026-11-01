"use client";

import { gsap } from "gsap";
import { useLayoutEffect, useRef } from "react";
import { BrandImage } from "@/components/brand/BrandImage";
import { motionAllowed, register } from "@/components/site/motion";

/**
 * The reference's one-time "middle tape": as the dark board arrives, a roll of clear tape drops in from above with a short
 * overshoot (measured: scale 0.82 -> 1.014 -> 1, 187 px of travel, about a second) while a clear strip unrolls down over the
 * board. It plays once and then rests, a little loose, over the kraft card. Hidden on a phone; with reduced motion it is just there.
 */
export function HangingTape() {
  const root = useRef<HTMLDivElement | null>(null);
  useLayoutEffect(() => {
    const el = root.current;
    if (!el || !motionAllowed()) return;
    register();
    const ctx = gsap.context(() => {
      const strip = el.querySelector("[data-strip]");
      const roll = el.querySelector("[data-roll]");
      const tl = gsap.timeline({ scrollTrigger: { trigger: el.parentElement, start: "top 55%", once: true } });
      tl.fromTo(el, { scale: 0.82, y: 187, autoAlpha: 0, transformOrigin: "50% 0%" }, { scale: 1, y: 0, autoAlpha: 1, duration: 1.3, ease: "back.out(2.2)" }, 0);
      // pulled out by a hand: the free end travels down fast, slows, and stops; the strip then sways once on its top edge
      tl.fromTo(strip, { scaleY: 0.02, transformOrigin: "50% 0%" }, { scaleY: 1, duration: 1.1, ease: "power3.out" }, 0.15);
      tl.fromTo(strip, { rotate: 5 }, { rotate: 0, duration: 1.6, ease: "elastic.out(1, 0.35)" }, 0.9);
      tl.fromTo(roll, { rotate: -140 }, { rotate: 0, duration: 1.3, ease: "power3.out" }, 0);
    }, el);
    return () => ctx.revert();
  }, []);
  return (
    <div ref={root} aria-hidden className="pointer-events-none absolute left-[40%] top-24 z-30 hidden w-32 md:block lg:left-[41%] lg:w-40">
      <div data-roll className="relative z-10 -mt-2">
        <BrandImage file="roll-small.png" alt="" decorative label="Tape" tone="cream" className="object-contain drop-shadow-xl" />
      </div>
      <div
        data-strip
        className="-mt-12 h-[30rem] w-full bg-gradient-to-r from-cream/10 via-cream/35 to-cream/10 shadow-[inset_0_0_0_1px_rgb(255_255_255/0.25)] backdrop-blur-[1px]"
        style={{ clipPath: "polygon(0 0,100% 0,100% 98%,92% 100%,84% 98%,76% 100%,68% 98%,60% 100%,52% 98%,44% 100%,36% 98%,28% 100%,20% 98%,12% 100%,4% 98%,0 100%)" }}
      />
    </div>
  );
}
