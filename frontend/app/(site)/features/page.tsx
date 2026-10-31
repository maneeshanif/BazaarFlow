import type { Metadata } from "next";
import Link from "next/link";
import { BrandImage } from "@/components/brand/BrandImage";
import { Chip } from "@/components/brand/Chip";
import type { Tone } from "@/components/brand/tones";
import { ClosingPanel } from "@/components/site/ClosingPanel";
import { MODULES } from "@/components/site/content";
import { Bob, Reveal } from "@/components/site/motion";
import { SubHero } from "@/components/site/SubHero";
import { CharText } from "@/components/site/text";

export const metadata: Metadata = {
  title: "What it handles - BazaarFlow",
  description: "Sales, orders, customers' udhaar, stock, vendors, money, an inbox and marketing posts, in one back-office for a small shop.",
};

const DISC: Record<string, string> = { sales: "disc-sales.png", khata: "disc-khata.png", stock: "disc-stock.png", money: "disc-money.png", inbox: "disc-chat.png", marketing: "disc-posts.png" };
const BG: Record<string, string> = { coral: "bg-coral", indigo: "bg-indigo text-cream", sunny: "bg-sunny", sky: "bg-sky", orange: "bg-orange", lime: "bg-lime" };

export default function FeaturesPage() {
  return (
    <>
      <SubHero chip="What it handles" lines={["Pick your", "tool."]} lead="Six parts of one back-office. Use the ones your shop needs today and leave the rest for later.">
        {/* overlapping discs, as on the reference's product page */}
        <ul className="mt-14 flex max-w-full flex-wrap items-center justify-center md:flex-nowrap md:[&>li+li]:-ms-6" aria-label="The six parts">
          {MODULES.map((m, i) => (
            <li key={m.key} className="relative">
              <Bob amount={14} seconds={3 + (i % 3) * 0.6}>
                <a
                  href={`#${m.key}`}
                  className="group block h-28 w-28 overflow-hidden rounded-full border-4 border-forest-ink shadow-card transition-transform duration-300 [transition-timing-function:var(--ease-bounce)] hover:z-10 hover:-translate-y-3 hover:rotate-6 hover:scale-110 focus-visible:z-10 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-line-focus md:h-40 md:w-40"
                  style={{ rotate: `${(i % 2 ? 6 : -6) + i}deg` }}
                >
                  <span className="sr-only">{m.name}</span>
                  <BrandImage file={DISC[m.key]} alt="" decorative label={m.name} tone={m.tone as Tone} />
                </a>
              </Bob>
            </li>
          ))}
        </ul>
      </SubHero>

      <section aria-label="Every part in detail" style={{ zIndex: 90 }} className="paper-forest relative -mt-16 overflow-hidden bg-forest-deep px-4 pb-28 pt-40 md:px-8">
        <ol className="mx-auto flex max-w-[110rem] flex-col gap-20">
          {MODULES.map((m, i) => (
            <li key={m.key} id={m.key} className={`grid scroll-mt-24 items-center gap-10 lg:grid-cols-2 ${i % 2 ? "lg:[direction:rtl]" : ""}`}>
              <Reveal y={60} className="lg:[direction:ltr]">
                <div className={`relative mx-auto aspect-square w-full max-w-md rounded-full ${BG[m.tone]} p-10 shadow-card`}>
                  <Bob amount={16} seconds={4} className="h-full w-full">
                    <div className="h-full w-full -rotate-6 overflow-hidden rounded-full">
                      <BrandImage file={DISC[m.key]} alt="" decorative label={m.name} tone="cream" />
                    </div>
                  </Bob>
                </div>
              </Reveal>
              <div className="lg:[direction:ltr]">
                <div className="flex items-center gap-3">
                  <Chip tone="tan">{`0${i + 1}`}</Chip>
                  {m.soon ? <Chip>Partly coming next</Chip> : null}
                </div>
                <CharText text={m.name} className="mt-4 font-display text-display-xl uppercase leading-[0.9] text-lime" />
                <p className="mt-4 max-w-prose text-ui-xl font-medium text-cream">{m.line}</p>
                <ul className="mt-6 flex max-w-prose flex-col gap-3 text-ui-lg text-cream">
                  {m.points.map((p) => (
                    <li key={p} className="rounded-card border-2 border-dotted border-lime/60 px-5 py-3">
                      {p}
                    </li>
                  ))}
                </ul>
              </div>
            </li>
          ))}
        </ol>
        <p className="mx-auto mt-20 max-w-[110rem] text-center text-ui-lg text-cream">
          Want to see them working?{" "}
          <Link href="/demo" className="font-bold text-lime underline decoration-dotted underline-offset-8">
            Open the live demo
          </Link>
          .
        </p>
      </section>

      <ClosingPanel zIndex={70} />
    </>
  );
}
