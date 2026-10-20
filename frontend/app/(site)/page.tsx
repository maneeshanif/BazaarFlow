import Link from "next/link";
import { BrandImage } from "@/components/brand/BrandImage";
import { Chip } from "@/components/brand/Chip";
import { TapeStrip } from "@/components/brand/TapeStrip";
import { TiltFrame } from "@/components/brand/TiltFrame";
import type { Tone } from "@/components/brand/tones";
import { HeroSlip } from "@/components/site/HeroSlip";
import { HeroStage } from "@/components/site/HeroStage";
import { Drift, Reveal, RollAcross, SplitHeading } from "@/components/site/motion";
import { SITE_ON_FOREST, SITE_ON_FOREST_SECONDARY, SITE_SECONDARY } from "@/components/site/styles";
import { StartDemoButton } from "@/components/site/StartDemoButton";

type Chapter = {
  id: string;
  tone: Tone;
  chip: string;
  title: string;
  say: string;
  does: string;
  photo: string;
  photoLabel: string;
  roll: string;
  slip?: boolean;
};

/** Four chapters, one per thing a shopkeeper says (the same four examples the page has always shown). */
const CHAPTERS: Chapter[] = [
  {
    id: "how",
    tone: "coral",
    chip: "Sales",
    title: "Say it. It is sold.",
    say: "2 shirt bech do Ali ko",
    does: "Writes the sale, takes 2 shirts off the shelf and adds Rs 5,000 to Ali's udhaar, once a manager approves it.",
    photo: "photo-shop-counter.jpg",
    photoLabel: "Shop counter",
    roll: "roll-sales.png",
    slip: true,
  },
  {
    id: "khata",
    tone: "indigo",
    chip: "Khata",
    title: "Every payment, written down.",
    say: "Ali ne 2000 diye",
    does: "Records Rs 2,000 from Ali and shows what he still owes.",
    photo: "photo-ledger.jpg",
    photoLabel: "Ledger",
    roll: "roll-khata.png",
  },
  {
    id: "ask",
    tone: "sunny",
    chip: "Ask",
    title: "Ask your own numbers.",
    say: "What did I sell today?",
    does: "Answers from your own sales: the total, the number of orders, and the profit if you are an owner or manager.",
    photo: "photo-parcels.jpg",
    photoLabel: "Parcels",
    roll: "roll-stock.png",
  },
  {
    id: "post",
    tone: "sky",
    chip: "Marketing",
    title: "Eid offer? Drafted.",
    say: "Write an Eid offer post",
    does: "Drafts it in your tone. You edit it and send it for approval. Publishing to Facebook comes later.",
    photo: "photo-market.jpg",
    photoLabel: "Bazaar",
    roll: "roll-chat.png",
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

const CONTROLS = [
  "Sales, payments and stock changes wait for a manager or the owner to approve them.",
  "Every conversation is logged with the tools it used. Names, phone numbers and emails are hidden in the log.",
  "The owner can pause the assistant at any moment, and each shop has a monthly AI allowance that stops it.",
  "Staff can chat and propose. Only owners and managers approve.",
];

const BAZAAR: { title: string; text: string; file: string; tone: Tone }[] = [
  { title: "Rupees and udhaar", text: "Prices in Rs, and a ledger for each customer with their purchases and payments.", file: "photo-ledger.jpg", tone: "coral" },
  { title: "English and Roman Urdu", text: "Write the way you talk. The assistant understands both.", file: "photo-shop-counter.jpg", tone: "sunny" },
  { title: "Made for a phone", text: "Every screen works at 360 px wide, because the counter is not a desk.", file: "photo-team.jpg", tone: "sky" },
  { title: "Your shop is yours", text: "One shop never sees another shop's data. Each demo is a private shop of its own.", file: "photo-parcels.jpg", tone: "indigo" },
];

/** Public landing page (PRD F-026), in the identity of ADR 0005. */
export default function LandingPage() {
  return (
    <>
      {/* 1. Hero: lime ground, display headline, the rolls */}
      <section style={{ zIndex: 100 }} className="paper-lime seam-arc relative overflow-hidden pb-24 pt-32 text-forest-ink md:pt-40">
        <div className="mx-auto grid max-w-[110rem] items-center gap-6 px-4 md:px-8 lg:grid-cols-[6fr_5fr]">
          <div>
            <Chip>BazaarFlow for shops</Chip>
            <SplitHeading as="h1" text="Tell it what you sold. It keeps the khata." className="mt-5 max-w-[14ch] text-display-lg lg:text-display-xl" />
            <p className="mt-6 max-w-prose text-ui-lg font-medium">
              BazaarFlow is a back-office for shops in Pakistan. Write a sale in English or Roman Urdu and it updates your stock and your customers&apos; udhaar.
              Nothing changes until you approve it.
            </p>
            <div className="mt-8 flex flex-wrap items-start gap-3">
              <StartDemoButton />
              <Link href="/register" className={SITE_SECONDARY}>
                Create your shop
              </Link>
            </div>
            <p className="mt-4 max-w-prose text-ui-sm font-medium">Free. The demo gives you a shop of your own for a day, with sales and customers already in it. No sign-up.</p>
          </div>
          <HeroStage />
        </div>
      </section>

      {/* 2. Statement on kraft card */}
      <section style={{ zIndex: 90 }} className="relative -mt-16 bg-forest-deep px-4 pb-24 pt-32 md:px-8" aria-labelledby="statement-title">
        <div className="paper-kraft relative mx-auto grid max-w-[90rem] gap-10 rounded-card p-8 shadow-card md:p-14 lg:grid-cols-[4fr_6fr] lg:items-center">
          <TapeStrip className="-top-3 left-12 h-10 w-36 -rotate-6" />
          <Drift className="mx-auto w-full max-w-sm" distance={30}>
            <TiltFrame tilt={-5} className="aspect-[3/4]">
              <BrandImage file="photo-shop-counter.jpg" alt="A shopkeeper at the counter with a phone" label="Shop counter" tone="sunny" />
            </TiltFrame>
          </Drift>
          <div>
            <SplitHeading id="statement-title" text="Eid rush. Udhaar chaos. Stock-take Sunday. We keep your khata straight." className="text-ui-3xl text-kraft-ink md:text-display-lg" />
            <Reveal delay={0.2} tilt={-3} className="mt-8 inline-block max-w-xs -rotate-2 rounded-chip bg-sunny p-5 font-slip text-ui-lg text-forest-ink shadow-card">
              <p>2 shirts for Ali</p>
              <p>reorder stock</p>
              <p>Eid offer post</p>
            </Reveal>
          </div>
        </div>
      </section>

      {/* 3. Chapters, one colour each */}
      {CHAPTERS.map((c, i) => (
        <section
          key={c.id}
          id={c.id}
          aria-labelledby={`${c.id}-title`}
          style={{ zIndex: 80 - i }}
          className={`seam-arc relative -mt-12 overflow-hidden pb-28 pt-24 text-forest-ink ${BG[c.tone]}`}
        >
          <RollAcross className="pointer-events-none absolute -top-10 left-0 h-40 w-40 overflow-hidden rounded-full" from={-2} to={9} spins={2}>
            <BrandImage file={c.roll} alt="" decorative label={c.chip} tone={c.tone === "indigo" ? "coral" : "cream"} />
          </RollAcross>
          <div className={`mx-auto grid max-w-[110rem] items-center gap-12 px-4 md:px-8 lg:grid-cols-2 ${i % 2 ? "lg:[direction:rtl]" : ""}`}>
            <Drift className="mx-auto w-full max-w-md lg:[direction:ltr]" distance={40}>
              <TiltFrame tilt={i % 2 ? -5 : 5} className="aspect-[4/5]">
                <BrandImage file={c.photo} alt="" decorative label={c.photoLabel} tone={c.tone === "indigo" ? "cream" : "forest"} />
              </TiltFrame>
            </Drift>
            <div className="lg:[direction:ltr]">
              <Chip tone="tan">{c.chip}</Chip>
              <SplitHeading id={`${c.id}-title`} text={c.title} className="mt-4 text-display-lg" />
              <Reveal delay={0.1}>
                <p className="mt-6 inline-block -rotate-1 rounded-chip bg-cream px-5 py-3 font-slip text-ui-xl text-forest-ink shadow-card">&ldquo;{c.say}&rdquo;</p>
                <p className="mt-5 max-w-prose text-ui-lg font-medium">{c.does}</p>
              </Reveal>
              {c.slip ? (
                <div className="mt-10 max-w-md text-forest-ink">
                  <HeroSlip />
                </div>
              ) : null}
            </div>
          </div>
        </section>
      ))}

      {/* 4. You stay in charge */}
      <section id="control" aria-labelledby="control-title" style={{ zIndex: 70 }} className="paper-forest seam-arc relative -mt-12 overflow-hidden bg-forest pb-28 pt-28">
        <div className="mx-auto grid max-w-[110rem] items-center gap-12 px-4 md:px-8 lg:grid-cols-[4fr_6fr]">
          <div className="flex justify-start lg:justify-center" aria-hidden="true">
            <div className="-rotate-[7deg] rounded-chip border-8 border-coral px-8 py-4 font-display text-ui-3xl uppercase tracking-wide text-coral md:text-display-lg">Approved</div>
          </div>
          <div>
            <SplitHeading id="control-title" text="You stay in charge of your shop." className="max-w-[16ch] text-display-lg text-lime" />
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

      {/* 5. Pill rows */}
      <section aria-labelledby="bazaar-title" style={{ zIndex: 60 }} className="relative -mt-12 overflow-hidden bg-forest-deep px-4 pb-24 pt-28 md:px-8">
        <SplitHeading id="bazaar-title" text="Built for how a bazaar shop works." className="mx-auto max-w-[110rem] text-display-lg text-lime" />
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

      {/* 6. Call to action band */}
      <section aria-labelledby="try-title" style={{ zIndex: 65 }} className="paper-lime seam-arc-top seam-arc relative -mt-12 px-4 pb-28 pt-32 text-forest-ink md:px-8">
        <div className="mx-auto grid max-w-[110rem] gap-6 lg:grid-cols-2">
          <TiltFrame tilt={-3} className="min-h-[22rem]">
            <BrandImage file="photo-family.jpg" alt="" decorative label="The family" tone="sunny" />
          </TiltFrame>
          <div className="rounded-card bg-forest p-8 text-cream shadow-card md:p-14">
            <SplitHeading id="try-title" text="See it in a shop that is already running." className="text-display-lg text-lime" />
            <p className="mt-5 max-w-prose text-ui-lg">A day of sales, eight products and three customers are waiting. Make a sale by chat and approve it yourself.</p>
            <div className="mt-8 flex flex-wrap items-start gap-3">
              <StartDemoButton className={SITE_ON_FOREST}>Try the live demo</StartDemoButton>
              <Link href="/register" className={SITE_ON_FOREST_SECONDARY}>
                Create your shop
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
