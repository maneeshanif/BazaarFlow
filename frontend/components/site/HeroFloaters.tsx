"use client";

import { gsap } from "gsap";
import { useLayoutEffect, useRef } from "react";
import { BrandImage } from "@/components/brand/BrandImage";
import { TiltFrame } from "@/components/brand/TiltFrame";
import { Bob, motionAllowed } from "@/components/site/motion";

type Floater = { id: string; at: string; depth: number; render: () => React.ReactNode };

const FLOATERS: Floater[] = [
  {
    id: "counter",
    at: "left-[3%] top-[44%] w-[13rem] xl:w-[16rem]",
    depth: 26,
    render: () => (
      <TiltFrame tilt={-8} className="aspect-[3/4]">
        <BrandImage file="photo-shop-counter.jpg" alt="" decorative label="Shop counter" tone="sunny" />
      </TiltFrame>
    ),
  },
  {
    id: "parcels",
    at: "right-[3%] top-[46%] w-[12rem] xl:w-[15rem]",
    depth: 34,
    render: () => (
      <TiltFrame tilt={8} className="aspect-[3/4]">
        <BrandImage file="photo-parcels.jpg" alt="" decorative label="Parcels" tone="coral" />
      </TiltFrame>
    ),
  },
  {
    id: "disc-sales",
    at: "left-[19%] top-[63%] w-24 xl:w-32",
    depth: -22,
    render: () => (
      <div className="aspect-square -rotate-12 overflow-hidden rounded-full shadow-card">
        <BrandImage file="disc-sales.png" alt="" decorative label="Sales" tone="cream" />
      </div>
    ),
  },
  {
    id: "disc-stock",
    at: "right-[19%] top-[66%] w-20 xl:w-28",
    depth: -30,
    render: () => (
      <div className="aspect-square rotate-12 overflow-hidden rounded-full shadow-card">
        <BrandImage file="disc-stock.png" alt="" decorative label="Stock" tone="cream" />
      </div>
    ),
  },
];

/**
 * Taped photos and round discs around the hero headline. They bob on their own and, with a mouse, slide a little against
 * the pointer at different depths, so the hero has layers (the reference's hero does the same). Wide screens only: on a
 * phone the headline has the room to itself. Pure decoration.
 */
export function HeroFloaters() {
  const root = useRef<HTMLDivElement | null>(null);
  useLayoutEffect(() => {
    const el = root.current;
    if (!el || !motionAllowed() || !window.matchMedia("(pointer: fine)").matches) return;
    const items = [...el.querySelectorAll<HTMLElement>("[data-depth]")];
    const movers = items.map((it) => ({ x: gsap.quickTo(it, "x", { duration: 0.8, ease: "power3.out" }), y: gsap.quickTo(it, "y", { duration: 0.8, ease: "power3.out" }), d: Number(it.dataset.depth) }));
    const move = (e: PointerEvent) => {
      const nx = e.clientX / window.innerWidth - 0.5;
      const ny = e.clientY / window.innerHeight - 0.5;
      movers.forEach((m) => {
        m.x(-nx * m.d);
        m.y(-ny * m.d * 0.7);
      });
    };
    window.addEventListener("pointermove", move, { passive: true });
    return () => window.removeEventListener("pointermove", move);
  }, []);
  return (
    <div ref={root} aria-hidden className="pointer-events-none absolute inset-0 hidden overflow-hidden lg:block">
      {FLOATERS.map((f, i) => (
        <div key={f.id} data-depth={f.depth} className={`absolute ${f.at}`}>
          <Bob amount={14 + i * 3} seconds={3.4 + i * 0.5}>
            {f.render()}
          </Bob>
        </div>
      ))}
    </div>
  );
}
