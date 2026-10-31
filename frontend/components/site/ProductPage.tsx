import type { ReactNode } from "react";
import { Chip } from "@/components/brand/Chip";
import { ClosingPanel } from "@/components/site/ClosingPanel";
import { CONTROLS } from "@/components/site/content";
import { Bob, Reveal } from "@/components/site/motion";
import { SubHero } from "@/components/site/SubHero";
import { CharText, WordText } from "@/components/site/text";

export type Step = { title: string; text: string; note: string; tone: string };
export type Fact = { label: string; text: string; later?: boolean };

/**
 * One public page about a single part of the product: the hero, numbered steps on the forest board, a taped "picture" slot
 * for whatever the page is about, a plain list of what works now and what comes next, and the shared control section.
 */
export function ProductPage({
  chip,
  lines,
  lead,
  steps,
  stepsTitle,
  facts,
  factsTitle,
  visual,
}: {
  chip: string;
  lines: string[];
  lead: string;
  steps: Step[];
  stepsTitle: string;
  facts: Fact[];
  factsTitle: string;
  visual: ReactNode;
}) {
  return (
    <>
      <SubHero chip={chip} lines={lines} lead={lead} />

      <section aria-labelledby="steps-title" style={{ zIndex: 90 }} className="paper-forest relative -mt-16 overflow-hidden bg-forest-deep px-4 pb-28 pt-36 md:px-8">
        <CharText id="steps-title" text={stepsTitle} className="mx-auto max-w-[110rem] font-display text-display-lg uppercase text-lime" />
        <ol className="mx-auto mt-14 flex max-w-[110rem] flex-col gap-14">
          {steps.map((s, i) => (
            <li key={s.title} className={`grid items-center gap-8 md:grid-cols-[auto_1fr_auto] ${i % 2 ? "md:[direction:rtl]" : ""}`}>
              <Reveal y={50} className="md:[direction:ltr]">
                <span className="grid h-28 w-28 place-items-center rounded-full bg-lime font-display text-display-lg text-forest-ink shadow-card md:h-40 md:w-40">{i + 1}</span>
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

      <section aria-labelledby="facts-title" style={{ zIndex: 80 }} className="paper-lime seam-arc relative -mt-12 px-4 pb-32 pt-36 text-forest-ink md:px-8">
        <div className="mx-auto grid max-w-[110rem] items-start gap-12 lg:grid-cols-2">
          <div>
            <CharText id="facts-title" text={factsTitle} className="font-display text-display-lg uppercase leading-[0.95]" />
            <ul className="mt-8 flex flex-col gap-4">
              {facts.map((f) => (
                <li key={f.label} className="rounded-card border-2 border-dotted border-forest-ink/60 bg-cream/60 px-6 py-4">
                  <div className="flex items-center gap-3">
                    <p className="font-display text-ui-xl uppercase">{f.label}</p>
                    <Chip tone={f.later ? "tan" : "forest"}>{f.later ? "Coming next" : "Works now"}</Chip>
                  </div>
                  <p className="mt-1 text-ui-base font-medium">{f.text}</p>
                </li>
              ))}
            </ul>
          </div>
          <Reveal y={60}>{visual}</Reveal>
        </div>
      </section>

      <section aria-labelledby="control-title" style={{ zIndex: 70 }} className="paper-forest seam-arc relative -mt-12 overflow-hidden bg-forest px-4 pb-32 pt-36 md:px-8">
        <CharText id="control-title" text="You stay in charge." className="mx-auto max-w-[110rem] font-display text-display-lg uppercase text-lime" />
        <ul className="mx-auto mt-8 flex max-w-prose flex-col gap-4 text-ui-lg text-cream">
          {CONTROLS.map((c) => (
            <li key={c} className="rounded-card border-2 border-dotted border-lime/60 px-6 py-4">
              {c}
            </li>
          ))}
        </ul>
      </section>

      <ClosingPanel zIndex={60} />
    </>
  );
}
