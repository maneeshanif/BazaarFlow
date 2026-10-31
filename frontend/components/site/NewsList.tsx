"use client";

import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { BrandImage } from "@/components/brand/BrandImage";
import type { Tone } from "@/components/brand/tones";
import { Bob } from "@/components/site/motion";

export type NewsItem = { id: string; kind: "Update" | "Next"; title: string; text: string; when: string; photo: string; tone: Tone; href?: string };

const KINDS = ["All", "Update", "Next"] as const;

/** The product notes with the reference's filter list (All, Event, News) beside a grid of dated cards. */
export function NewsList({ items }: { items: NewsItem[] }) {
  const [kind, setKind] = useState<(typeof KINDS)[number]>("All");
  const shown = items.filter((i) => kind === "All" || i.kind === kind);
  const count = (k: (typeof KINDS)[number]) => items.filter((i) => k === "All" || i.kind === k).length;
  return (
    <div className="mx-auto grid max-w-[110rem] gap-10 lg:grid-cols-[16rem_1fr]">
      <div role="tablist" aria-label="Filter the notes" className="flex gap-4 lg:flex-col">
        {KINDS.map((k) => (
          <button
            key={k}
            type="button"
            role="tab"
            aria-selected={kind === k}
            onClick={() => setKind(k)}
            className={`roll flex items-baseline gap-2 border-b-2 border-dotted border-lime/60 pb-2 text-start font-display text-display-lg uppercase transition-colors focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-lime ${
              kind === k ? "text-lime" : "text-lime/40 hover:text-lime/80"
            }`}
          >
            <span>{k}</span>
            <sup className="font-slip text-ui-sm">{count(k)}</sup>
          </button>
        ))}
      </div>
      <ul aria-live="polite" className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
        {shown.map((n, i) => (
          <li key={n.id}>
            <Bob amount={8 + (i % 3) * 3} seconds={4 + (i % 4) * 0.5}>
              <article className="tilt-hover flex h-full flex-col overflow-hidden rounded-card bg-cream text-forest-ink shadow-card">
                <div className="aspect-[4/3]">
                  <BrandImage file={n.photo} alt="" decorative label={n.title} tone={n.tone} />
                </div>
                <div className="flex flex-1 flex-col p-5">
                  <p className="font-display text-ui-xs uppercase tracking-widest text-forest-ink/70">{n.kind}</p>
                  <h3 className="mt-1 font-display text-ui-xl uppercase leading-tight">{n.title}</h3>
                  <p className="mt-2 flex-1 text-ui-base font-medium">{n.text}</p>
                  <div className="mt-4 flex items-end justify-between">
                    <p className="font-display text-ui-2xl uppercase leading-none">{n.when}</p>
                    {n.href ? (
                      <Link href={n.href} aria-label={`Open: ${n.title}`} className="grid h-9 w-9 place-items-center rounded-full bg-lime text-forest-ink transition-transform duration-300 [transition-timing-function:var(--ease-bounce)] hover:scale-125 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-line-focus">
                        <ArrowUpRight aria-hidden className="h-4 w-4" />
                      </Link>
                    ) : null}
                  </div>
                </div>
              </article>
            </Bob>
          </li>
        ))}
      </ul>
    </div>
  );
}
