import Link from "next/link";
import { BrandImage } from "@/components/brand/BrandImage";
import type { Tone } from "@/components/brand/tones";
import { Board } from "@/components/site/Board";
import { Chapters } from "@/components/site/Chapters";
import { ClosingPanel } from "@/components/site/ClosingPanel";
import { CONTROLS } from "@/components/site/content";
import { GiantStory } from "@/components/site/GiantStory";
import { HeroFloaters } from "@/components/site/HeroFloaters";
import { HeroHeadline } from "@/components/site/HeroHeadline";
import { HeroStage } from "@/components/site/HeroStage";
import { Reveal } from "@/components/site/motion";
import { CharText, RollLabel, WordText } from "@/components/site/text";
import { SITE_SECONDARY } from "@/components/site/styles";
import { SpinBadge } from "@/components/site/SpinBadge";
import { StartDemoButton } from "@/components/site/StartDemoButton";
import { WaveBand } from "@/components/site/WaveBand";

const BAZAAR: { title: string; text: string; file: string; tone: Tone }[] = [
  { title: "Rupees and udhaar", text: "Prices in Rs, and a ledger for each customer with their purchases and payments.", file: "photo-ledger.jpg", tone: "coral" },
  { title: "English and Roman Urdu", text: "Write the way you talk. The assistant understands both.", file: "photo-shop-counter.jpg", tone: "sunny" },
  { title: "Made for a phone", text: "Every screen works at 360 px wide, because the counter is not a desk.", file: "photo-delivery-bag.jpg", tone: "sky" },
  { title: "Your shop is yours", text: "One shop never sees another shop's data. Each demo is a private shop of its own.", file: "photo-team.jpg", tone: "indigo" },
];

/** Public landing page (PRD F-026), in the identity of ADR 0005 and the reference sequence in home-motion-measured.md. */
export default function LandingPage() {
  return (
    <>
      {/* 1. Hero: crumpled lime paper, small line, huge hand-cut words, taped photos and discs that drift, parcels rising from behind the curve */}
      <section
        aria-label="BazaarFlow"
        style={{ zIndex: 100 }}
        className="paper-lime seam-arc relative flex min-h-screen flex-col items-center px-4 pb-44 pt-28 text-forest-ink md:px-8 md:pb-56 md:pt-24"
      >
        <HeroFloaters />
        <p className="absolute start-4 top-20 max-w-[16rem] border-s-2 border-dotted border-forest-ink ps-3 font-display text-ui-base uppercase leading-tight md:start-8">
          Keeping a small shop&apos;s books, from the first sale to the last parcel
        </p>
        <SpinBadge text="Small shops, big orders" className="absolute end-6 top-44 hidden h-28 w-28 md:block lg:end-[6%] lg:top-[22%] lg:h-40 lg:w-40" />
        <div className="relative mt-12 w-full max-w-[110rem] md:mt-8">
          <HeroHeadline />
        </div>
        <WordText
          text="BazaarFlow is a back-office for shops in Pakistan that pack and send out orders. Write a sale in English or Roman Urdu and it updates your stock and your customers' udhaar. Nothing changes until you approve it."
          className="relative mx-auto mt-6 max-w-prose text-center text-ui-lg font-medium"
        />
        <div className="relative mt-6 flex flex-wrap items-start justify-center gap-3">
          <StartDemoButton />
          <Link href="/register" className={SITE_SECONDARY}>
            <RollLabel text="Create your shop" />
          </Link>
        </div>
        <p className="relative mt-3 max-w-prose text-center text-ui-sm font-medium">Free. The demo gives you a shop of your own for a day, with sales and customers already in it. No sign-up.</p>
        <div className="absolute inset-x-0 bottom-0 z-[110] mx-auto w-full max-w-3xl translate-y-1/3">
          <HeroStage />
        </div>
      </section>

      {/* 2. Forest board: things taped to dark paper that slide past at different speeds */}
      <Board />

      {/* 3. Wavy ribbon */}
      <WaveBand />

      {/* 4. The four chapters as a disc slider */}
      <Chapters />

      {/* 5. Pinned story: huge words slide across while photos and discs bob */}
      <GiantStory />

      {/* 6. You stay in charge */}
      <section id="control" aria-labelledby="control-title" style={{ zIndex: 70 }} className="paper-forest seam-arc relative -mt-12 overflow-hidden bg-forest pb-28 pt-28">
        <div className="mx-auto grid max-w-[110rem] items-center gap-12 px-4 md:px-8 lg:grid-cols-[4fr_6fr]">
          <div className="flex justify-start lg:justify-center" aria-hidden="true">
            <div className="-rotate-[7deg] rounded-chip border-8 border-coral px-8 py-4 font-display text-ui-3xl uppercase tracking-wide text-coral md:text-display-lg">Approved</div>
          </div>
          <div>
            <CharText id="control-title" text="You stay in charge of your shop." className="max-w-[16ch] text-display-lg text-lime" />
            <ul className="mt-8 flex max-w-prose flex-col gap-4 text-ui-lg text-cream">
              {CONTROLS.map((c) => (
                <li key={c} className="rounded-card border-2 border-dotted border-lime/60 px-6 py-4">
                  {c}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* 7. Pill rows */}
      <section aria-labelledby="bazaar-title" style={{ zIndex: 60 }} className="relative -mt-12 overflow-hidden bg-forest-deep px-4 pb-24 pt-28 md:px-8">
        <CharText id="bazaar-title" text="Built for how a bazaar shop works." className="mx-auto max-w-[110rem] text-display-lg text-lime" />
        <ul className="mx-auto mt-12 flex max-w-[110rem] flex-col gap-5">
          {BAZAAR.map((b, i) => (
            <li key={b.title}>
              <Reveal delay={i * 0.05} y={40}>
                <div className="flex flex-wrap items-center gap-6 rounded-pill bg-forest p-3 pe-10 md:flex-nowrap">
                  <div className="h-24 w-24 shrink-0 overflow-hidden rounded-full md:h-28 md:w-28">
                    <BrandImage file={b.file} alt="" decorative label={b.title} tone={b.tone} />
                  </div>
                  <h3 className="font-display text-ui-2xl uppercase text-lime md:w-1/3">{b.title}</h3>
                  <p className="max-w-prose text-ui-lg text-cream">{b.text}</p>
                </div>
              </Reveal>
            </li>
          ))}
        </ul>
      </section>

      {/* 8. Closing panel */}
      <ClosingPanel />
    </>
  );
}
