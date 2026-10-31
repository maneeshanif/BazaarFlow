import { BrandImage } from "@/components/brand/BrandImage";
import { TapeStrip } from "@/components/brand/TapeStrip";
import { TiltFrame } from "@/components/brand/TiltFrame";
import { Bob, Drift, WaveText } from "@/components/site/motion";
import { ScrubText } from "@/components/site/text";

const TODO = ["pack Ali's order", "count flour and rice", "settle Sana's udhaar"];

/**
 * The forest board: loose things taped and clipped to dark paper that slide past at different speeds as the page scrolls
 * (the reference does this right after its hero). Serious in subject, a working shop's worries; playful only in how it moves.
 */
export function Board() {
  return (
    <section aria-labelledby="board-title" style={{ zIndex: 90 }} className="paper-forest relative -mt-16 overflow-hidden bg-forest-deep px-4 pb-32 pt-40 md:px-8">
      <div className="mx-auto grid max-w-[110rem] gap-y-16 md:grid-cols-12 md:gap-x-8 md:gap-y-24">
        {/* sticky note with a clip */}
        <Drift distance={50} className="md:col-span-4 md:col-start-1 md:row-start-1 md:mt-10">
          <Bob amount={10} seconds={4} className="relative mx-auto w-full max-w-xs -rotate-3">
            <div aria-hidden className="absolute -left-3 top-8 z-20 h-10 w-5 rotate-[-20deg] rounded-[3px] border-2 border-forest-ink bg-kraft-ink shadow-popover" />
            <div className="relative rounded-chip bg-sunny p-6 pt-8 text-forest-ink shadow-card">
              <TapeStrip className="-top-4 left-1/2 h-9 w-28 -translate-x-1/2 rotate-1" />
              <p className="font-display text-ui-2xl uppercase">To do</p>
              <ul className="mt-3 space-y-2 font-slip text-ui-lg">
                {TODO.map((t) => (
                  <li key={t} className="flex items-center gap-3 border-b border-forest-ink/30 pb-1">
                    <span aria-hidden className="h-4 w-4 shrink-0 rounded-full border-2 border-forest-ink" />
                    {t}
                  </li>
                ))}
              </ul>
            </div>
          </Bob>
        </Drift>

        {/* kraft card with the statement */}
        <Drift distance={30} className="md:col-span-7 md:col-start-6 md:row-span-2 md:row-start-1">
          <div className="paper-kraft relative rounded-card p-8 shadow-card md:p-14">
            <TapeStrip className="-top-4 right-16 h-10 w-40 rotate-2" />
            <h2 id="board-title" className="font-display text-ui-3xl uppercase leading-[0.95] text-kraft-ink md:text-display-lg">
              <ScrubText text="Order rush. Udhaar chaos. Stock-take Sunday." className="block" />
              <ScrubText text="A parcel with the wrong address." className="mt-3 block" />
              <WaveText text="We keep it straight." className="mt-3 block" />
            </h2>
          </div>
        </Drift>

        {/* produce illustration */}
        <Drift distance={60} className="md:col-span-4 md:col-start-2 md:row-start-2">
          <Bob amount={14} seconds={5}>
            <TiltFrame tilt={-8} className="mx-auto aspect-[4/3] w-full max-w-sm">
              <BrandImage file="illus-produce.jpg" alt="" decorative label="Peaches and tomatoes" tone="sunny" />
            </TiltFrame>
          </Bob>
          <p aria-hidden className="mt-6 text-center font-slip text-ui-lg text-lime">
            built for the everyday order
          </p>
        </Drift>

        {/* photos */}
        <Drift distance={80} className="md:col-span-4 md:col-start-3 md:row-start-3">
          <Bob amount={12} seconds={4.5}>
            <TiltFrame tilt={5} className="mx-auto aspect-[3/4] w-full max-w-xs">
              <BrandImage file="photo-parcels.jpg" alt="Hands holding two small parcels sealed with tape" label="Parcels" tone="coral" />
            </TiltFrame>
          </Bob>
        </Drift>
        <Drift distance={40} className="md:col-span-4 md:col-start-8 md:row-start-3 md:mt-24">
          <Bob amount={16} seconds={3.6}>
            <TiltFrame tilt={-5} className="mx-auto aspect-[3/4] w-full max-w-xs">
              <BrandImage file="photo-food-pack.jpg" alt="Hands closing a box of hot food for delivery" label="Packed food" tone="sky" />
            </TiltFrame>
          </Bob>
        </Drift>
      </div>
    </section>
  );
}
