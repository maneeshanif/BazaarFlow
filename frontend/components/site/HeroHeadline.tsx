"use client";

import { useRef, useSyncExternalStore, type CSSProperties } from "react";
import { INTRO_SECONDS, introWillPlay } from "@/components/site/intro-state";
import { BrandImage } from "@/components/brand/BrandImage";

/** Fixed, hand-picked turns and drops, so each letter looks cut from paper and the page never differs between renders. */
const TURN = [-4, 3, -2, 4, -3, 2, -5, 3, -2, 4, -1, 2];
const DROP = [0, 2, -2, 3, -1, 2, -3, 1, 3, -2, 2, -1];

function CutWord({ text, from }: { text: string; from: number }) {
  let n = from;
  return (
    <span className="inline-block whitespace-nowrap">
      {Array.from(text).map((ch, i) => {
        const k = n++;
        const style = { "--r": `${TURN[k % TURN.length]}deg`, "--r0": `${TURN[(k + 5) % TURN.length] * 3}deg`, "--dy": `${DROP[k % DROP.length]}%`, "--delay": `${0.05 * k}s` } as CSSProperties;
        return (
          <span key={i} data-cut className="cut-letter" style={style}>
            {ch === " " ? " " : ch}
          </span>
        );
      })}
    </span>
  );
}

/**
 * The hero headline: a small line with the logo badge in the middle, then two lines of very large hand-cut capitals. The
 * whole sentence is exposed once to assistive technology. The letters drop in after the opening has cleared, and the
 * big lines lean away from the pointer a little as it moves over the hero (the reference does the same).
 */
export function HeroHeadline() {
  const intro = useSyncExternalStore(
    () => () => {},
    introWillPlay,
    () => false,
  );
  const lean = useRef<HTMLDivElement | null>(null);
  const move = (e: React.PointerEvent) => {
    const el = lean.current;
    if (!el || e.pointerType !== "mouse") return;
    const r = el.getBoundingClientRect();
    const dx = (e.clientX - (r.left + r.width / 2)) / r.width;
    const dy = (e.clientY - (r.top + r.height / 2)) / r.height;
    el.style.transform = `perspective(900px) rotateY(${dx * 5}deg) rotateX(${-dy * 4}deg)`;
  };
  const rest = () => {
    if (lean.current) lean.current.style.transform = "";
  };
  return (
    <div onPointerMove={move} onPointerLeave={rest} style={{ "--base": `${intro ? INTRO_SECONDS : 0.1}s` } as CSSProperties}>
      <h1 className="text-center font-display uppercase text-forest-ink">
        <span className="sr-only">Tell it what you sold. It keeps the khata.</span>
        <span aria-hidden className="block">
          <span className="hero-small flex items-center justify-center gap-3 md:gap-6">
            <span>Tell it</span>
            <span className="inline-block h-[2em] w-[3.8em] shrink-0 -rotate-6 overflow-hidden rounded-chip">
              <BrandImage file="logo-badge.png" alt="" decorative label="BazaarFlow" tone="forest" />
            </span>
            <span>what you sold.</span>
          </span>
          <span ref={lean} className="mt-2 block transition-transform duration-200 ease-out will-change-transform md:mt-4">
            <span className="hero-giant block">
              <CutWord text="It keeps" from={0} />
            </span>
            <span className="hero-giant block">
              <CutWord text="the khata" from={8} />
            </span>
          </span>
        </span>
      </h1>
    </div>
  );
}
