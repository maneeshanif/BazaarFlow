"use client";

import { useEffect, useRef } from "react";

/** Things that get the "hand" version of the cursor. */
const HAND = "a, button, [role=button], [role=tab], summary, label, select, [data-cursor=hand]";

/**
 * The arrow that replaces the system cursor on the public site (ADR 0005, measured on the reference in
 * home-motion-measured.md): a cream arrow turned a few degrees that follows the pointer with a short lag and grows into a
 * "hand" over anything clickable. Only for a fine pointer and only when motion is allowed; everyone else keeps their own
 * cursor. Pure decoration, so it is hidden from assistive technology. It moves through direct style writes, not state.
 */
export function Cursor() {
  const ref = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (!window.matchMedia("(pointer: fine)").matches || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const root = document.documentElement;
    let x = -100;
    let y = -100;
    let cx = x;
    let cy = y;
    let raf = 0;
    const tick = () => {
      cx += (x - cx) * 0.3;
      cy += (y - cy) * 0.3;
      el.style.transform = `translate3d(${cx}px, ${cy}px, 0)`;
      raf = requestAnimationFrame(tick);
    };
    const move = (e: PointerEvent) => {
      if (!el.dataset.show) {
        cx = e.clientX;
        cy = e.clientY;
        el.dataset.show = "1";
      }
      x = e.clientX;
      y = e.clientY;
    };
    const over = (e: PointerEvent) => {
      el.dataset.hand = (e.target as Element | null)?.closest?.(HAND) ? "1" : "0";
    };
    const down = () => {
      el.dataset.press = "1";
    };
    const up = () => {
      delete el.dataset.press;
    };
    const leave = () => {
      delete el.dataset.show;
    };
    root.classList.add("has-cursor");
    window.addEventListener("pointermove", move, { passive: true });
    window.addEventListener("pointerdown", down);
    window.addEventListener("pointerup", up);
    document.addEventListener("pointerover", over);
    root.addEventListener("pointerleave", leave);
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      root.classList.remove("has-cursor");
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerdown", down);
      window.removeEventListener("pointerup", up);
      document.removeEventListener("pointerover", over);
      root.removeEventListener("pointerleave", leave);
    };
  }, []);
  return (
    <div ref={ref} aria-hidden data-testid="cursor-arrow" className="group pointer-events-none fixed left-0 top-0 z-[200] opacity-0 data-[show=1]:opacity-100">
      <svg
        viewBox="0 0 24 28"
        className="-ms-1 -mt-0.5 h-8 w-7 rotate-[7deg] drop-shadow-md transition-transform duration-200 [transition-timing-function:var(--ease-bounce)] group-data-[hand=1]:-rotate-[12deg] group-data-[hand=1]:scale-[1.35] group-data-[press=1]:scale-90"
      >
        <path d="M3 2 L3 22 L8.4 17.2 L11.8 25 L15.4 23.4 L12 15.8 L19.4 15.8 Z" strokeWidth="2" strokeLinejoin="round" className="fill-cream stroke-forest-ink group-data-[hand=1]:fill-lime" />
      </svg>
    </div>
  );
}
