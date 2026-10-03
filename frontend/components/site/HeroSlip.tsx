"use client";

import { gsap } from "gsap";
import { useCallback, useEffect, useLayoutEffect, useRef } from "react";

const SAID = "2 shirt bech do Ali ko";

/**
 * The one orchestrated moment on the landing page: a sale typed the way a shopkeeper would say it, the draft that
 * answers it, the slip that fills in (sale, stock, Ali's udhaar) and the red approval stamp that lands last.
 *
 * The finished state is plain HTML, so it is what search engines, screen readers and anyone who prefers reduced motion
 * see. The script only hides the parts it is about to reveal, and only when motion is allowed.
 */
export function HeroSlip() {
  const root = useRef<HTMLDivElement | null>(null);
  const timeline = useRef<gsap.core.Timeline | null>(null);

  const build = useCallback((): gsap.core.Timeline | null => {
    const el = root.current;
    if (!el || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return null;
    const q = <T extends Element>(selector: string) => el.querySelector<T>(selector);
    const all = (selector: string) => Array.from(el.querySelectorAll(selector));
    const typed = q<HTMLElement>("[data-typed]");
    const stock = q<HTMLElement>("[data-stock]");
    const owed = q<HTMLElement>("[data-owed]");
    if (!typed || !stock || !owed) return null;

    const state = { chars: 0, stock: 12, owed: 0 };
    const tl = gsap.timeline({ defaults: { ease: "power2.out" } });
    tl.set(["[data-reply]", "[data-yes]"], { autoAlpha: 0, y: 8 })
      .set(all("[data-line]"), { autoAlpha: 0, x: -10 })
      .set("[data-stamp]", { autoAlpha: 0, scale: 2.4, rotate: -16 })
      .set(typed, { textContent: "" })
      .set(stock, { textContent: "12" })
      .set(owed, { textContent: "0" });

    tl.to(state, {
      chars: SAID.length,
      duration: 1.5,
      ease: "none",
      delay: 0.5,
      onUpdate: () => {
        typed.textContent = SAID.slice(0, Math.round(state.chars));
      },
    })
      .to("[data-reply]", { autoAlpha: 1, y: 0, duration: 0.45 }, "+=0.35")
      .to("[data-yes]", { autoAlpha: 1, y: 0, duration: 0.35 }, "+=0.9")
      .to(all("[data-line]"), { autoAlpha: 1, x: 0, duration: 0.4, stagger: 0.28 }, "+=0.2")
      .to(state, { stock: 10, duration: 0.5, ease: "power1.inOut", onUpdate: () => void (stock.textContent = String(Math.round(state.stock))) }, "<0.1")
      .to(state, { owed: 5000, duration: 0.8, ease: "power1.out", onUpdate: () => void (owed.textContent = Math.round(state.owed).toLocaleString("en-US")) }, "<0.3")
      .to("[data-stamp]", { autoAlpha: 1, scale: 1, rotate: -7, duration: 0.28, ease: "power4.in" }, "+=0.35")
      .to("[data-slip]", { x: 3, duration: 0.05, repeat: 5, yoyo: true, ease: "none" }, ">")
      .to("[data-slip]", { x: 0, duration: 0.08 });
    return tl;
  }, []);

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      timeline.current = build();
    }, root);
    return () => ctx.revert();
  }, [build]);

  useEffect(() => () => void timeline.current?.kill(), []);

  const replay = () => timeline.current?.restart();

  return (
    <figure ref={root} className="m-0 overflow-x-clip">
      <p className="sr-only">
        Example: the shopkeeper writes &quot;{SAID}&quot;. The assistant drafts a sale of 2 Cotton Shirts to Ali Raza for Rs 5,000 on udhaar and asks to post it.
        After approval the stock of Cotton Shirt goes from 12 to 10 and Ali owes Rs 5,000.
      </p>
      <div aria-hidden="true" className="flex flex-col gap-4">
        <div className="rounded-lg border border-ledger-rule bg-ledger-raised p-4">
          <div className="flex flex-col gap-3 text-ui-base">
            <div className="ml-auto max-w-[85%] rounded-lg bg-ink px-3 py-2 text-fg-inverse">
              <span data-typed>{SAID}</span>
            </div>
            <div data-reply className="max-w-[90%] rounded-lg border border-ledger-rule bg-ledger px-3 py-2 text-ink">
              Draft: 2 x Cotton Shirt to Ali Raza, Rs 5,000, on udhaar. Post it?
            </div>
            <div data-yes className="ml-auto max-w-[85%] rounded-lg bg-ink px-3 py-2 text-fg-inverse">
              haan
            </div>
          </div>
        </div>

        <div data-slip className="relative rounded-lg border border-ledger-rule bg-ledger-raised">
          <div className="ledger-rules ledger-margin px-4 pb-10 pl-14 pt-3 font-slip text-ui-sm leading-[1.8rem] text-ink">
            <p data-line className="font-semibold">
              Sale, today
            </p>
            <p data-line className="flex justify-between gap-3">
              <span>2 x Cotton Shirt</span>
              <span className="tabular-nums">5,000</span>
            </p>
            <p data-line className="flex justify-between gap-3">
              <span>Cotton Shirt in stock</span>
              <span className="tabular-nums" data-stock>
                10
              </span>
            </p>
            <p data-line className="flex justify-between gap-3">
              <span>Ali owes (udhaar)</span>
              <span className="tabular-nums">
                Rs <span data-owed>5,000</span>
              </span>
            </p>
          </div>
          <div
            data-stamp
            className="pointer-events-none absolute -bottom-4 right-4 -rotate-[7deg] select-none rounded-md border-4 border-stamp px-3 py-1 font-display text-ui-xl tracking-wide text-stamp mix-blend-multiply"
          >
            APPROVED
          </div>
        </div>
      </div>
      <figcaption className="mt-6 flex items-center justify-between gap-3 text-ui-xs text-ink-soft">
        <span>A sale, written the way you would say it.</span>
        <button type="button" onClick={replay} className="rounded-md px-2 py-1 font-medium text-ink underline underline-offset-4 hover:bg-ledger-rule/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-focus">
          Replay
        </button>
      </figcaption>
    </figure>
  );
}
