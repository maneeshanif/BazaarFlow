import type { Metadata } from "next";
import { ClosingPanel } from "@/components/site/ClosingPanel";
import { CONTROLS } from "@/components/site/content";
import { HeroSlip } from "@/components/site/HeroSlip";
import { Bob, Reveal } from "@/components/site/motion";
import { SubHero } from "@/components/site/SubHero";
import { CharText, WordText } from "@/components/site/text";

export const metadata: Metadata = {
  title: "How it works - BazaarFlow",
  description: "Write what happened in English or Roman Urdu. BazaarFlow drafts it, you approve it, and your stock and udhaar are written down.",
};

const STEPS = [
  { n: 1, title: "Say it", text: "Write the sale the way you would say it, in English or Roman Urdu.", note: "2 shirt bech do Ali ko", tone: "bg-sunny" },
  { n: 2, title: "Check it", text: "The assistant drafts it: 2 x Cotton Shirt to Ali Raza, Rs 5,000, on udhaar. Nothing has changed yet.", note: "Draft: Rs 5,000, on udhaar. Post it?", tone: "bg-cream" },
  { n: 3, title: "Approve it", text: "A manager or the owner approves. Staff can propose but cannot approve.", note: "haan", tone: "bg-lime" },
  { n: 4, title: "It is written", text: "Stock goes from 12 to 10, Ali owes Rs 5,000, and the whole thing is in the activity log.", note: "stock 12 -> 10", tone: "bg-sky" },
];

const SAYINGS = [
  ["Sell", "2 shirt bech do Ali ko", "Drafts the sale and takes the stock off the shelf once approved."],
  ["Collect", "Ali ne 2000 diye", "Records Rs 2,000 from Ali and shows what he still owes."],
  ["Ask", "What did I sell today?", "Answers from your own sales: the total, the orders, the profit for owners and managers."],
  ["Post", "Write an Eid offer post", "Drafts it in your tone for you to edit and send for approval."],
] as const;

export default function HowItWorksPage() {
  return (
    <>
      <SubHero
        chip="How it works"
        lines={["Four steps,", "one sentence."]}
        lead="Write what happened. BazaarFlow drafts it, you approve it, and the books are written."
      />

      {/* the four steps on the forest board */}
      <section aria-labelledby="steps-title" style={{ zIndex: 90 }} className="paper-forest relative -mt-16 overflow-hidden bg-forest-deep px-4 pb-28 pt-36 md:px-8">
        <h2 id="steps-title" className="sr-only">
          The four steps
        </h2>
        <ol className="mx-auto flex max-w-[110rem] flex-col gap-16">
          {STEPS.map((s, i) => (
            <li key={s.n} className={`grid items-center gap-8 md:grid-cols-[auto_1fr_auto] ${i % 2 ? "md:[direction:rtl]" : ""}`}>
              <Reveal y={50} className="md:[direction:ltr]">
                <span className="grid h-32 w-32 place-items-center rounded-full bg-lime font-display text-display-lg text-forest-ink shadow-card md:h-44 md:w-44">{s.n}</span>
              </Reveal>
              <div className="md:[direction:ltr]">
                <CharText text={s.title} className="font-display text-display-xl uppercase leading-[0.9] text-lime" />
                <WordText text={s.text} className="mt-4 max-w-prose text-ui-xl text-cream" />
              </div>
              <Bob amount={12} seconds={3.5 + i * 0.4} className="md:[direction:ltr]">
                <p aria-hidden className={`${s.tone} max-w-[14rem] -rotate-3 rounded-chip p-5 font-slip text-ui-lg text-forest-ink shadow-card`}>
                  {s.note}
                </p>
              </Bob>
            </li>
          ))}
        </ol>
      </section>

      {/* the example, drawn */}
      <section aria-labelledby="see-title" style={{ zIndex: 80 }} className="paper-lime seam-arc relative -mt-12 px-4 pb-32 pt-36 text-forest-ink md:px-8">
        <div className="mx-auto grid max-w-[110rem] items-center gap-12 lg:grid-cols-2">
          <div>
            <CharText id="see-title" text="See one sale go through." className="font-display text-display-lg uppercase leading-[0.95]" />
            <WordText text="This is the real example from the home page: a sentence, a draft, a yes, and then a line in the ledger." className="mt-5 max-w-prose text-ui-lg font-medium" />
          </div>
          <HeroSlip />
        </div>
      </section>

      {/* what you can say */}
      <section aria-labelledby="say-title" style={{ zIndex: 70 }} className="paper-forest seam-arc relative -mt-12 overflow-hidden bg-forest px-4 pb-32 pt-36 md:px-8">
        <div className="mx-auto max-w-[110rem]">
          <CharText id="say-title" text="Four things you can say." className="font-display text-display-lg uppercase text-lime" />
          <ul className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {SAYINGS.map(([verb, said, does], i) => (
              <li key={verb}>
                <Bob amount={10 + i * 3} seconds={4 + i * 0.4}>
                  <div className="h-full rounded-card bg-cream p-6 text-forest-ink shadow-card tilt-hover">
                    <p className="font-display text-ui-2xl uppercase">{verb}</p>
                    <p className="mt-3 inline-block -rotate-1 rounded-chip bg-sunny px-3 py-2 font-slip text-ui-lg">&ldquo;{said}&rdquo;</p>
                    <p className="mt-4 text-ui-base font-medium">{does}</p>
                  </div>
                </Bob>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* control */}
      <section id="control" aria-labelledby="control-title" style={{ zIndex: 65 }} className="paper-lime seam-arc relative -mt-12 px-4 pb-32 pt-36 text-forest-ink md:px-8">
        <div className="mx-auto grid max-w-[110rem] items-center gap-12 lg:grid-cols-[4fr_6fr]">
          <div className="mx-auto w-full max-w-sm" aria-hidden>
            <Bob amount={14} seconds={4}>
              <div className="-rotate-[7deg] rounded-chip border-8 border-coral px-8 py-4 text-center font-display text-ui-3xl uppercase tracking-wide text-coral md:text-display-lg">Approved</div>
            </Bob>
          </div>
          <div>
            <CharText id="control-title" text="You stay in charge of your shop." className="max-w-[16ch] font-display text-display-lg uppercase leading-[0.95]" />
            <ul className="mt-8 flex max-w-prose flex-col gap-4 text-ui-lg font-medium">
              {CONTROLS.map((c) => (
                <li key={c} className="rounded-card border-2 border-dotted border-forest-ink/60 bg-cream/60 px-6 py-4">
                  {c}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <ClosingPanel zIndex={60} />
    </>
  );
}
