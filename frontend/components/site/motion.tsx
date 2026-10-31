"use client";

import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { Fragment, useLayoutEffect, useRef, type ElementType, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { CharText } from "@/components/site/text";

/**
 * Scroll motion for the public site (ADR 0005). Everything is visible in the server-rendered HTML; the scripts below
 * hide a piece only when they are about to animate it, and only when the visitor has not asked for reduced motion.
 */
let registered = false;
export function register() {
  if (!registered) {
    gsap.registerPlugin(ScrollTrigger);
    registered = true;
  }
}
export const motionAllowed = () => typeof window !== "undefined" && !window.matchMedia("(prefers-reduced-motion: reduce)").matches;

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
 * A display heading whose letters rise one after another and react to the pointer. The text is exposed once, whole, to
 * assistive technology; the split letters are decoration. (Kept under this name; the work is in `text.tsx`.)
 */
export function SplitHeading({ text, as, className, id }: { text: string; as?: ElementType; className?: string; id?: string }) {
  return <CharText text={text} as={as} className={className} id={id} />;
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

/**
 * Floats its children gently up and down for as long as they are on screen, each piece at its own pace so a group never
 * moves in step (the reference's drifting photos and discs do the same).
 */
export function Bob({ children, className, amount = 18, seconds = 3 }: { children: ReactNode; className?: string; amount?: number; seconds?: number }) {
  const ref = useRef<HTMLDivElement | null>(null);
  useLayoutEffect(() => {
    if (!motionAllowed() || !ref.current) return;
    register();
    const ctx = gsap.context(() => {
      const tween = gsap.to(ref.current, { y: -amount, rotate: gsap.utils.random(-3, 3), duration: seconds * gsap.utils.random(0.8, 1.3), ease: "sine.inOut", repeat: -1, yoyo: true, paused: true });
      ScrollTrigger.create({ trigger: ref.current, start: "top bottom", end: "bottom top", onToggle: (self) => (self.isActive ? tween.play() : tween.pause()) });
    }, ref);
    return () => ctx.revert();
  }, [amount, seconds]);
  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}

/**
 * Text whose letters hop up and down in a wave while it is on screen (the kraft card on the reference does this on its
 * last lines). The sentence is exposed once to assistive technology; the letters are decoration.
 */
export function WaveText({ text, className, amount = 0.14 }: { text: string; className?: string; amount?: number }) {
  const ref = useRef<HTMLSpanElement | null>(null);
  useLayoutEffect(() => {
    if (!motionAllowed() || !ref.current) return;
    register();
    const ctx = gsap.context(() => {
      const tween = gsap.to(ref.current!.querySelectorAll("[data-wave]"), { yPercent: -amount * 100, duration: 0.5, ease: "sine.inOut", repeat: -1, yoyo: true, stagger: { each: 0.07, repeat: -1, yoyo: true }, paused: true });
      ScrollTrigger.create({ trigger: ref.current, start: "top bottom", end: "bottom top", onToggle: (self) => (self.isActive ? tween.play() : tween.pause()) });
    }, ref);
    return () => ctx.revert();
  }, [amount]);
  return (
    <span ref={ref} className={className}>
      <span className="sr-only">{text}</span>
      <span aria-hidden>
        {text.split(" ").map((word, w, all) => (
          <Fragment key={w}>
            <span className="inline-block whitespace-nowrap">
              {Array.from(word).map((ch, i) => (
                <span key={i} data-wave className="inline-block">
                  {ch}
                </span>
              ))}
            </span>
            {w < all.length - 1 ? " " : null}
          </Fragment>
        ))}
      </span>
    </span>
  );
}
