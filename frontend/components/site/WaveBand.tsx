"use client";

import { gsap } from "gsap";
import { useLayoutEffect, useRef } from "react";
import { motionAllowed, register } from "@/components/site/motion";

const LINE = "When the orders pile up, something has to keep count.  ";

/**
 * The wavy lime ribbon between the board and the chapters: huge capitals follow a curve and slide along it as the page
 * scrolls (the reference does the same with a sentence that runs off the edge). Decoration; the sentence is read once.
 */
export function WaveBand() {
  const path = useRef<SVGTextPathElement | null>(null);
  const root = useRef<HTMLElement | null>(null);
  useLayoutEffect(() => {
    if (!motionAllowed() || !path.current || !root.current) return;
    register();
    const ctx = gsap.context(() => {
      const state = { offset: 0 };
      gsap.to(state, {
        offset: -1400,
        ease: "none",
        scrollTrigger: { trigger: root.current, start: "top bottom", end: "bottom top", scrub: 0.5 },
        onUpdate: () => path.current?.setAttribute("startOffset", String(state.offset)),
      });
    }, root);
    return () => ctx.revert();
  }, []);
  return (
    <section ref={root} aria-label="When the orders pile up, something has to keep count." style={{ zIndex: 85 }} className="relative -mt-24 h-56 overflow-hidden md:h-72">
      <svg viewBox="0 0 1440 300" preserveAspectRatio="xMidYMid slice" className="absolute inset-0 h-full w-full" aria-hidden>
        <defs>
          <path id="wave-path" d="M-200 170 C 100 40, 380 270, 720 160 S 1300 30, 1700 150" />
        </defs>
        <use href="#wave-path" className="fill-none stroke-lime" strokeWidth="190" />
        <text className="fill-forest-ink font-display uppercase" style={{ fontSize: 130 }}>
          <textPath ref={path} href="#wave-path" startOffset="0">
            {LINE.repeat(4)}
          </textPath>
        </text>
      </svg>
    </section>
  );
}
