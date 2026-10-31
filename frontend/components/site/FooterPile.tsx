"use client";

import { gsap } from "gsap";
import Link from "next/link";
import { useLayoutEffect, useRef } from "react";
import { BrandImage } from "@/components/brand/BrandImage";
import type { Tone } from "@/components/brand/tones";
import { motionAllowed, register } from "@/components/site/motion";

const DISCS: { file: string; label: string; tone: Tone; at: string }[] = [
  { file: "disc-khata.png", label: "Khata", tone: "indigo", at: "left-[12%] bottom-[6%] h-36 w-36 lg:h-48 lg:w-48" },
  { file: "disc-stock.png", label: "Stock", tone: "sunny", at: "left-[30%] bottom-[2%] h-32 w-32 lg:h-44 lg:w-44" },
  { file: "disc-sales.png", label: "Sales", tone: "coral", at: "right-[28%] bottom-[8%] h-36 w-36 lg:h-48 lg:w-48" },
  { file: "disc-money.png", label: "Money", tone: "sky", at: "right-[10%] bottom-[3%] h-32 w-32 lg:h-44 lg:w-44" },
];

const CIRCLES: { href: string; label: string; at: string }[] = [
  { href: "/demo", label: "Demo", at: "left-[3%] bottom-[10%]" },
  { href: "/sign-in", label: "Sign in", at: "right-[2%] bottom-[22%]" },
];

/**
 * The piled-up footer scene of the reference: round discs and lime circular links lie in front of the wordmark as if they had
 * just dropped in. They fall into place the first time the footer scrolls into view; with reduced motion they are just there.
 */
export function FooterPile() {
  const root = useRef<HTMLDivElement | null>(null);
  useLayoutEffect(() => {
    if (!motionAllowed() || !root.current) return;
    register();
    const ctx = gsap.context(() => {
      gsap.from("[data-drop]", {
        y: () => -gsap.utils.random(320, 560),
        rotate: () => gsap.utils.random(-120, 120),
        autoAlpha: 0,
        duration: 1.2,
        ease: "bounce.out",
        stagger: 0.14,
        scrollTrigger: { trigger: root.current, start: "top 75%", once: true },
      });
    }, root);
    return () => ctx.revert();
  }, []);
  return (
    <div ref={root} className="pointer-events-none absolute inset-0 hidden md:block">
      {DISCS.map((d, i) => (
        <div key={d.file} data-drop aria-hidden className={`absolute overflow-hidden rounded-full shadow-card ${d.at}`} style={{ rotate: `${i % 2 ? 14 : -12}deg` }}>
          <BrandImage file={d.file} alt="" decorative label={d.label} tone={d.tone} />
        </div>
      ))}
      {CIRCLES.map((c) => (
        <Link
          key={c.href}
          href={c.href}
          data-drop
          className={`pointer-events-auto absolute grid h-24 w-24 place-items-center rounded-full bg-lime font-display text-ui-lg uppercase text-forest-ink transition-transform duration-300 [transition-timing-function:var(--ease-bounce)] hover:scale-110 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-cream lg:h-32 lg:w-32 ${c.at}`}
        >
          {c.label}
        </Link>
      ))}
    </div>
  );
}
