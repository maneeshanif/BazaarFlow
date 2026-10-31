"use client";

import Link from "next/link";
import { useId, useRef, useState, type KeyboardEvent } from "react";
import { BrandImage } from "@/components/brand/BrandImage";
import { Chip } from "@/components/brand/Chip";
import { TiltFrame } from "@/components/brand/TiltFrame";
import type { Tone } from "@/components/brand/tones";
import { HeroSlip } from "@/components/site/HeroSlip";
import { Bob, SplitHeading } from "@/components/site/motion";

type Chapter = {
  id: string;
  tone: Tone;
  chip: string;
  word: string;
  title: string;
  say: string;
  does: string;
  photo: string;
  photoLabel: string;
  disc: string;
  slip?: boolean;
};

/** Four chapters, one per thing a shopkeeper says (the same four examples the page has always shown). */
const CHAPTERS: Chapter[] = [
  {
    id: "how",
    tone: "coral",
    chip: "Sales",
    word: "Sales",
    title: "Say it. It is sold.",
    say: "2 shirt bech do Ali ko",
    does: "Writes the sale, takes 2 shirts off the shelf and adds Rs 5,000 to Ali's udhaar, once a manager approves it.",
    photo: "photo-shop-counter.jpg",
    photoLabel: "Shop counter",
    disc: "disc-sales.png",
    slip: true,
  },
  {
    id: "khata",
    tone: "indigo",
    chip: "Khata",
    word: "Khata",
    title: "Every payment, written down.",
    say: "Ali ne 2000 diye",
    does: "Records Rs 2,000 from Ali and shows what he still owes.",
    photo: "photo-ledger.jpg",
    photoLabel: "Ledger",
    disc: "disc-khata.png",
  },
  {
    id: "ask",
    tone: "sunny",
    chip: "Ask",
    word: "Stock",
    title: "Ask your own numbers.",
    say: "What did I sell today?",
    does: "Answers from your own sales: the total, the number of orders, and the profit if you are an owner or manager.",
    photo: "photo-small-goods.jpg",
    photoLabel: "Small goods",
    disc: "disc-stock.png",
  },
  {
    id: "post",
    tone: "sky",
    chip: "Marketing",
    word: "Posts",
    title: "Eid offer? Drafted.",
    say: "Write an Eid offer post",
    does: "Drafts it in your tone. You edit it and send it for approval. Publishing to Facebook comes later.",
    photo: "photo-market.jpg",
    photoLabel: "Bazaar",
    disc: "disc-posts.png",
  },
];

const BG: Record<Tone, string> = {
  lime: "bg-lime",
  coral: "bg-coral",
  orange: "bg-orange",
  sunny: "bg-sunny",
  sky: "bg-sky",
  indigo: "bg-indigo text-cream",
  forest: "bg-forest text-cream",
  cream: "bg-cream",
};

/**
 * The chapters as the reference's product slider: one big round disc in the middle, its name set huge behind it, the
 * other discs stacked to the side to switch to, and the whole section changing colour with the chapter. Every chapter's
 * text stays in the page (the inactive ones are hidden), and the discs are a proper tab list with arrow-key support.
 */
export function Chapters() {
  const [active, setActive] = useState(0);
  const uid = useId();
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  const c = CHAPTERS[active];
  const dark = c.tone === "indigo";

  const key = (e: KeyboardEvent, i: number) => {
    const next = e.key === "ArrowDown" || e.key === "ArrowRight" ? (i + 1) % CHAPTERS.length : e.key === "ArrowUp" || e.key === "ArrowLeft" ? (i + CHAPTERS.length - 1) % CHAPTERS.length : -1;
    if (next < 0) return;
    e.preventDefault();
    setActive(next);
    tabs.current[next]?.focus();
  };

  return (
    <section
      aria-label="How it works"
      style={{ zIndex: 80 }}
      className={`seam-arc relative -mt-32 overflow-hidden pb-28 pt-44 text-forest-ink transition-colors duration-700 ${BG[c.tone]}`}
    >
      <span id="how" aria-hidden className="absolute top-0" />
      <div className="mx-auto grid max-w-[110rem] grid-cols-1 items-center gap-10 px-4 md:px-8 lg:grid-cols-[5fr_5fr_auto]">
        {/* what it does */}
        <div className="order-2 lg:order-1">
          {CHAPTERS.map((ch, i) => (
            <div key={ch.id} id={i === 0 ? undefined : ch.id} role="tabpanel" aria-labelledby={`${uid}-tab-${i}`} hidden={i !== active}>
              <Chip tone="tan">{ch.chip}</Chip>
              <SplitHeading text={ch.title} className="mt-4 text-display-lg" />
              <p className="mt-6 inline-block -rotate-1 rounded-chip bg-cream px-5 py-3 font-slip text-ui-xl text-forest-ink shadow-card">&ldquo;{ch.say}&rdquo;</p>
              <p className="mt-5 max-w-prose text-ui-lg font-medium">{ch.does}</p>
              {ch.slip ? (
                <div className="mt-10 max-w-md text-forest-ink">
                  <HeroSlip />
                </div>
              ) : null}
            </div>
          ))}
        </div>

        {/* the disc with its name behind it */}
        <div className="relative order-1 mx-auto flex aspect-square w-full max-w-xl items-center justify-center lg:order-2">
          <svg aria-hidden key={c.word} viewBox="0 0 600 600" className="absolute inset-0 h-full w-full" style={{ animation: "logo-pop 0.7s var(--ease-bounce) both" }}>
            <defs>
              <path id={`${uid}-arc`} d="M 20 300 A 280 280 0 0 0 580 300" />
            </defs>
            <text className={`font-display uppercase ${dark ? "fill-cream/25" : "fill-cream/60"}`} style={{ fontSize: 190 }} textAnchor="middle">
              <textPath href={`#${uid}-arc`} startOffset="50%">
                {c.word}
              </textPath>
            </text>
          </svg>
          <Bob amount={14} seconds={4} className="relative z-10 w-3/5">
            <div key={c.id} className="aspect-square -rotate-6 overflow-hidden rounded-full shadow-card" style={{ animation: "logo-pop 0.7s var(--ease-bounce) both" }}>
              <BrandImage file={c.disc} alt="" decorative label={c.word} tone="cream" />
            </div>
          </Bob>
          <Link
            href="/demo"
            className="absolute right-[6%] top-[8%] z-20 grid h-28 w-28 place-items-center rounded-full bg-cream font-display text-ui-xl uppercase text-forest-ink shadow-card outline-dotted outline-2 outline-offset-4 outline-forest-ink transition-transform duration-300 [transition-timing-function:var(--ease-bounce)] hover:scale-110 hover:-rotate-6 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-line-focus"
          >
            Try it
          </Link>
          <Bob amount={20} seconds={5} className="absolute -left-2 bottom-2 z-20 hidden w-2/5 md:block">
            <TiltFrame tilt={-8} className="aspect-[4/5]">
              <BrandImage file={c.photo} alt="" decorative label={c.photoLabel} tone="forest" />
            </TiltFrame>
          </Bob>
        </div>

        {/* the other discs */}
        <div role="tablist" aria-label="Chapters" aria-orientation="vertical" className="order-3 flex flex-wrap justify-center gap-4 lg:flex-col">
          {CHAPTERS.map((ch, i) => (
            <button
              key={ch.id}
              ref={(el) => {
                tabs.current[i] = el;
              }}
              id={`${uid}-tab-${i}`}
              type="button"
              role="tab"
              aria-selected={i === active}
              tabIndex={i === active ? 0 : -1}
              onClick={() => setActive(i)}
              onKeyDown={(e) => key(e, i)}
              className={`h-20 w-20 overflow-hidden rounded-full border-4 transition-transform duration-300 [transition-timing-function:var(--ease-bounce)] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-line-focus md:h-24 md:w-24 ${
                i === active ? "scale-110 border-forest-ink shadow-card" : "border-cream hover:scale-105"
              }`}
            >
              <span className="sr-only">{ch.chip}</span>
              <BrandImage file={ch.disc} alt="" decorative label={ch.chip} tone="cream" />
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
