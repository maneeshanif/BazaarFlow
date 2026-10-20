"use client";

import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { createElement, useLayoutEffect, useRef, type ElementType, type ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Scroll motion for the public site (ADR 0005). Everything is visible in the server-rendered HTML; the scripts below
 * hide a piece only when they are about to animate it, and only when the visitor has not asked for reduced motion.
 */
let registered = false;
function register() {
  if (!registered) {
    gsap.registerPlugin(ScrollTrigger);
    registered = true;
  }
}
const motionAllowed = () => typeof window !== "undefined" && !window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Fades and lifts its children into place the first time they scroll into view. */
export function Reveal({ children, className, y = 60, delay = 0, tilt = 0 }: { children: ReactNode; className?: string; y?: number; delay?: number; tilt?: number }) {
  const ref = useRef<HTMLDivElement | null>(null);
  useLayoutEffect(() => {
    if (!motionAllowed() || !ref.current) return;
    register();
    const ctx = gsap.context(() => {
      gsap.from(ref.current, { autoAlpha: 0, y, rotate: tilt, duration: 0.9, delay, ease: "back.out(1.4)", scrollTrigger: { trigger: ref.current, start: "top 85%", once: true } });
    }, ref);
    return () => ctx.revert();
  }, [y, delay, tilt]);
  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}

/**
 * A display heading whose letters rise one after another. The text is exposed once, whole, to assistive technology;
 * the split letters are decoration.
 */
export function SplitHeading({ text, as: Tag = "h2", className, id }: { text: string; as?: ElementType; className?: string; id?: string }) {
  const ref = useRef<HTMLSpanElement | null>(null);
  useLayoutEffect(() => {
    if (!motionAllowed() || !ref.current) return;
    register();
    const ctx = gsap.context(() => {
      const letters = ref.current!.querySelectorAll("[data-letter]");
      gsap.from(letters, {
        yPercent: 110,
        rotate: () => gsap.utils.random(-14, 14),
        duration: 0.8,
        stagger: 0.025,
        ease: "back.out(1.6)",
        scrollTrigger: { trigger: ref.current, start: "top 88%", once: true },
      });
    }, ref);
    return () => ctx.revert();
  }, [text]);
  const words = text.split(" ");
  return createElement(
    Tag,
    { id, className },
    <span ref={ref}>
      <span className="sr-only">{text}</span>
      <span aria-hidden>
        {words.map((word, w) => (
          <span key={w} className="inline-block whitespace-nowrap">
            {Array.from(word).map((ch, i) => (
              <span key={i} className="inline-block overflow-hidden align-bottom">
                <span data-letter className="inline-block">
                  {ch}
                </span>
              </span>
            ))}
            {w < words.length - 1 ? " " : null}
          </span>
        ))}
      </span>
    </span>,
  );
}

/** Rolls its child across the section as the visitor scrolls, turning as it goes (the tape rolls in from the edge). */
export function RollAcross({ children, className, from = -20, to = 80, spins = 1 }: { children: ReactNode; className?: string; from?: number; to?: number; spins?: number }) {
  const ref = useRef<HTMLDivElement | null>(null);
  useLayoutEffect(() => {
    if (!motionAllowed() || !ref.current) return;
    register();
    const ctx = gsap.context(() => {
      gsap.fromTo(
        ref.current,
        { xPercent: from * 10, rotate: 0 },
        { xPercent: to * 10, rotate: 360 * spins, ease: "none", scrollTrigger: { trigger: ref.current, start: "top bottom", end: "bottom top", scrub: 0.6 } },
      );
    }, ref);
    return () => ctx.revert();
  }, [from, to, spins]);
  return (
    <div ref={ref} aria-hidden className={cn("will-change-transform", className)}>
      {children}
    </div>
  );
}

/** Slow vertical drift for tilted photos so they float against the page as it scrolls. */
export function Drift({ children, className, distance = 60 }: { children: ReactNode; className?: string; distance?: number }) {
  const ref = useRef<HTMLDivElement | null>(null);
  useLayoutEffect(() => {
    if (!motionAllowed() || !ref.current) return;
    register();
    const ctx = gsap.context(() => {
      gsap.fromTo(ref.current, { y: distance }, { y: -distance, ease: "none", scrollTrigger: { trigger: ref.current, start: "top bottom", end: "bottom top", scrub: 0.8 } });
    }, ref);
    return () => ctx.revert();
  }, [distance]);
  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}
