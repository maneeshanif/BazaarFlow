"use client";

import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { createElement, Fragment, useEffect, useLayoutEffect, useRef, type ElementType, type RefObject } from "react";
import { cn } from "@/lib/utils";

/**
 * Text that behaves the way the reference's text does (measured in home-motion-measured.md):
 * letters and words sit in clipping wrappers and rise into place when they scroll into view, and while the pointer is
 * over them the ones near it lift, tilt away from it and grow a little, then settle again. Everything is decoration over
 * one plain sentence that is read once by assistive technology.
 */
let registered = false;
function register() {
  if (!registered) {
    gsap.registerPlugin(ScrollTrigger);
    registered = true;
  }
}
const motionAllowed = () => typeof window !== "undefined" && !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const finePointer = () => typeof window !== "undefined" && window.matchMedia("(pointer: fine)").matches;

type Proximity = {
  /** how far the pointer reaches, in font sizes */
  radius: number;
  /** how high the nearest piece lifts, in font sizes */
  lift: number;
  /** degrees of tilt away from the pointer */
  tilt: number;
  /** extra scale at the nearest piece, 0.07 = 7% */
  grow: number;
};

export const PROXIMITY_HEADING: Proximity = { radius: 2.4, lift: 0.075, tilt: 5, grow: 0.07 };
export const PROXIMITY_WORDS: Proximity = { radius: 3.2, lift: 0.22, tilt: 3, grow: 0.04 };

/**
 * While a mouse is over `root`, moves every `[data-prox]` piece toward a target worked out from its distance to the
 * pointer (nearest: lifted, grown, upright; further: less; beyond the radius: at rest). The pieces ease toward their
 * targets each frame, so they settle softly when the pointer leaves. Not for touch, not for reduced motion.
 */
export function useProximity(root: RefObject<HTMLElement | null>, opts: Proximity) {
  const { radius, lift, tilt, grow } = opts;
  useEffect(() => {
    const el = root.current;
    if (!el || (lift === 0 && grow === 0) || !finePointer() || !motionAllowed()) return;
    // each piece is measured in its own font size, so a small line and a giant word in one block both feel right
    const items = [...el.querySelectorAll<HTMLElement>("[data-prox]")].map((node) => ({ node, y: 0, r: 0, s: 1, em: parseFloat(getComputedStyle(node).fontSize) || 16 }));
    if (!items.length) return;
    let px = 0;
    let py = 0;
    let inside = false;
    let raf = 0;
    const tick = () => {
      let moving = false;
      for (const it of items) {
        // measure the wrapper, which does not move, so the target does not chase itself
        const box = (it.node.parentElement ?? it.node).getBoundingClientRect();
        const dx = px - (box.left + box.width / 2);
        const dy = py - (box.top + box.height / 2);
        const em = it.em;
        const dist = Math.hypot(dx, dy * 0.6);
        const w = inside ? Math.max(0, 1 - dist / (radius * em)) ** 1.7 : 0;
        const away = Math.sign(-dx) * Math.min(1, Math.abs(dx) / (em * 0.9));
        const ty = -lift * em * w;
        const tr = -away * tilt * w;
        const ts = 1 + grow * w;
        it.y += (ty - it.y) * 0.2;
        it.r += (tr - it.r) * 0.2;
        it.s += (ts - it.s) * 0.2;
        const rest = Math.abs(ty - it.y) < 0.02 && Math.abs(tr - it.r) < 0.01 && Math.abs(ts - it.s) < 0.0005 && w === 0;
        if (!rest) moving = true;
        it.node.style.transform = rest ? "" : `translate3d(0, ${it.y.toFixed(2)}px, 0) rotate(${it.r.toFixed(2)}deg) scale(${it.s.toFixed(4)})`;
      }
      raf = inside || moving ? requestAnimationFrame(tick) : 0;
    };
    const move = (e: PointerEvent) => {
      if (e.pointerType !== "mouse") return;
      px = e.clientX;
      py = e.clientY;
      inside = true;
      if (!raf) raf = requestAnimationFrame(tick);
    };
    const leave = () => {
      inside = false;
      if (!raf) raf = requestAnimationFrame(tick);
    };
    el.addEventListener("pointermove", move);
    el.addEventListener("pointerleave", leave);
    return () => {
      el.removeEventListener("pointermove", move);
      el.removeEventListener("pointerleave", leave);
      cancelAnimationFrame(raf);
      for (const it of items) it.node.style.transform = "";
    };
  }, [root, radius, lift, tilt, grow]);
}

type CharProps = {
  text: string;
  as?: ElementType;
  className?: string;
  id?: string;
  /** letters rise into place on scroll (default) */
  reveal?: boolean;
  /** letters react to the pointer (default) */
  hover?: boolean;
  /** seconds to wait before the letters rise, for headings that follow an opening */
  delay?: number;
};

/** A heading made of letters: rise on scroll, react to the pointer. The text is exposed once, whole, to assistive technology. */
export function CharText({ text, as: Tag = "h2", className, id, reveal = true, hover = true, delay = 0 }: CharProps) {
  const ref = useRef<HTMLSpanElement | null>(null);
  useLayoutEffect(() => {
    const root = ref.current;
    if (!root) return;
    const clips = root.querySelectorAll<HTMLElement>(".clip");
    const free = () => clips.forEach((c) => c.setAttribute("data-free", ""));
    if (!reveal || !motionAllowed()) {
      free();
      return;
    }
    register();
    const ctx = gsap.context(() => {
      gsap.from(root.querySelectorAll("[data-char]"), {
        yPercent: 130,
        duration: 0.85,
        delay,
        stagger: 0.028,
        ease: "power3.out",
        onComplete: free,
        scrollTrigger: { trigger: root, start: "top 90%", once: true },
      });
    }, root);
    return () => ctx.revert();
  }, [text, reveal, delay]);
  useProximity(ref, hover ? PROXIMITY_HEADING : { radius: 0, lift: 0, tilt: 0, grow: 0 });
  const words = text.split(" ");
  return createElement(
    Tag,
    { id, className },
    <span ref={ref}>
      <span className="sr-only">{text}</span>
      <span aria-hidden>
        {words.map((word, w) => (
          <Fragment key={w}>
            <span className="inline-block whitespace-nowrap">
              {Array.from(word).map((ch, i) => (
                <span key={i} className="clip">
                  <span data-char data-prox className="char">
                    {ch}
                  </span>
                </span>
              ))}
            </span>
            {w < words.length - 1 ? " " : null}
          </Fragment>
        ))}
      </span>
    </span>,
  );
}

/** A paragraph made of words: rise one after another on scroll, lift when the pointer passes. */
export function WordText({ text, as: Tag = "p", className, id, delay = 0 }: Omit<CharProps, "reveal" | "hover">) {
  const ref = useRef<HTMLSpanElement | null>(null);
  useLayoutEffect(() => {
    const root = ref.current;
    if (!root) return;
    const clips = root.querySelectorAll<HTMLElement>(".clip");
    const free = () => clips.forEach((c) => c.setAttribute("data-free", ""));
    if (!motionAllowed()) {
      free();
      return;
    }
    register();
    const ctx = gsap.context(() => {
      gsap.from(root.querySelectorAll("[data-word]"), {
        yPercent: 110,
        duration: 0.7,
        delay,
        stagger: 0.025,
        ease: "power2.out",
        onComplete: free,
        scrollTrigger: { trigger: root, start: "top 92%", once: true },
      });
    }, root);
    return () => ctx.revert();
  }, [text, delay]);
  useProximity(ref, PROXIMITY_WORDS);
  const words = text.split(" ");
  return createElement(
    Tag,
    { id, className },
    <span ref={ref}>
      <span className="sr-only">{text}</span>
      <span aria-hidden>
        {words.map((word, w) => (
          <Fragment key={w}>
            <span className="clip">
              <span data-word data-prox className="char">
                {word}
              </span>
            </span>
            {w < words.length - 1 ? " " : null}
          </Fragment>
        ))}
      </span>
    </span>,
  );
}

/**
 * A label whose letters roll out of the top and back in from below when the nearest `.roll` ancestor (a link or
 * button) is hovered or focused: 0.45 s a letter, 35 ms apart (measured on the reference's footer links).
 */
export function RollLabel({ text, className }: { text: string; className?: string }) {
  return (
    <span className={cn("inline-block", className)}>
      <span className="sr-only">{text}</span>
      <span aria-hidden>
        {Array.from(text).map((ch, i) => (
          <span key={i} className="roll-clip">
            <span className="roll-char" style={{ "--i": i } as React.CSSProperties}>
              {ch === " " ? " " : ch}
            </span>
          </span>
        ))}
      </span>
    </span>
  );
}

/**
 * Text whose letters are pulled up out of their clips by the scroll itself (not once, but back and forth with the
 * visitor's position), so a line looks sliced while it is half revealed. The kraft card on the reference does this.
 */
export function ScrubText({ text, className }: { text: string; className?: string }) {
  const ref = useRef<HTMLSpanElement | null>(null);
  useLayoutEffect(() => {
    const root = ref.current;
    if (!root || !motionAllowed()) return;
    register();
    const ctx = gsap.context(() => {
      gsap.fromTo(
        root.querySelectorAll("[data-char]"),
        { yPercent: 105 },
        {
          yPercent: 0,
          ease: "none",
          stagger: 0.04,
          scrollTrigger: {
            trigger: root,
            start: "top 95%",
            end: "top 55%",
            scrub: 0.5,
            // once fully risen the clips let the pointer lift the letters out of them
            onUpdate: (self) => root.querySelectorAll(".clip").forEach((c) => (self.progress >= 1 ? c.setAttribute("data-free", "") : c.removeAttribute("data-free"))),
          },
        },
      );
    }, root);
    return () => ctx.revert();
  }, [text]);
  useProximity(ref, PROXIMITY_HEADING);
  const words = text.split(" ");
  return (
    <span ref={ref} className={className}>
      <span className="sr-only">{text}</span>
      <span aria-hidden>
        {words.map((word, w) => (
          <Fragment key={w}>
            <span className="inline-block whitespace-nowrap">
              {Array.from(word).map((ch, i) => (
                <span key={i} className="clip">
                  <span data-char data-prox className="char">
                    {ch}
                  </span>
                </span>
              ))}
            </span>
            {w < words.length - 1 ? " " : null}
          </Fragment>
        ))}
      </span>
    </span>
  );
}
