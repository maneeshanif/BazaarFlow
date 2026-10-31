"use client";

import Link from "next/link";
import { Fragment, useEffect, useId, useRef, useState } from "react";
import { ArrowUpRight } from "lucide-react";

export type MenuLink = { label: string; href: string };

/** Each letter drops in on its own, a little after the one before (the reference does the same on its sheet). */
function DropLetters({ text, open, base }: { text: string; open: boolean; base: number }) {
  let n = 0;
  return (
    <>
      <span className="sr-only">{text}</span>
      <span aria-hidden>
        {text.split(" ").map((word, w, all) => (
          <Fragment key={w}>
            <span className="inline-block whitespace-nowrap">
              {Array.from(word).map((ch, i) => {
                const k = n++;
                return (
                  <span
                    key={i}
                    className="inline-block transition-[transform,opacity] duration-500 [transition-timing-function:var(--ease-bounce)]"
                    style={{ transform: open ? "none" : "translateY(-110%) rotate(-8deg)", opacity: open ? 1 : 0, transitionDelay: open ? `${base + k * 25}ms` : "0ms" }}
                  >
                    {ch}
                  </span>
                );
              })}
            </span>
            {w < all.length - 1 ? " " : null}
          </Fragment>
        ))}
      </span>
    </>
  );
}

/**
 * The public site's menu: a cream paper tab at the top right. Pulling it (click or Enter) drops a sheet of big links and
 * the tab rides down with the sheet's lower edge; pull again, press Escape or follow a link to put it away.
 */
export function MenuTab({ links }: { links: MenuLink[] }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const root = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (!open) return;
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    const outside = (e: PointerEvent) => {
      if (root.current && !root.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", key);
    document.addEventListener("pointerdown", outside);
    return () => {
      document.removeEventListener("keydown", key);
      document.removeEventListener("pointerdown", outside);
    };
  }, [open]);
  return (
    <div ref={root} className="fixed right-3 top-0 z-[120] w-[min(28rem,calc(100vw-1.5rem))] md:right-6">
      <nav
        id={id}
        aria-label="Main"
        // closed: collapsed and inert, so its links are not in the tab order
        {...(open ? {} : { inert: true })}
        className="paper-cream overflow-hidden rounded-b-card shadow-card transition-[max-height] duration-700 [transition-timing-function:cubic-bezier(0.7,0,0.3,1)]"
        style={{ maxHeight: open ? "34rem" : "0" }}
      >
        <ul className="px-4 pb-3 pt-2">
          {links.map((l, i) => (
            <li key={l.href} className="border-t-2 border-dotted border-forest-ink first:border-t-0">
              <Link
                href={l.href}
                onClick={() => setOpen(false)}
                className="group flex items-center justify-between gap-3 py-3 font-display text-ui-2xl uppercase leading-none text-forest-ink focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-line-focus md:text-ui-3xl"
              >
                <span>
                  <DropLetters text={l.label} open={open} base={250 + i * 90} />
                </span>
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-lime text-forest-ink transition-transform duration-300 [transition-timing-function:var(--ease-bounce)] group-hover:scale-125 group-focus-visible:scale-125">
                  <ArrowUpRight aria-hidden className="h-4 w-4" />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
        className="menu-tab-shape paper-cream group relative ms-auto block h-20 w-[8.5rem] pb-3 pt-2 text-center font-display text-ui-lg uppercase tracking-wide text-forest-ink focus-visible:outline-none"
      >
        <span aria-hidden className="mx-2 block border-t-2 border-dotted border-forest-ink" />
        <span className="mt-3 block rounded-chip px-2 group-focus-visible:ring-4 group-focus-visible:ring-line-focus">{open ? "Close" : "Menu"}</span>
      </button>
    </div>
  );
}
