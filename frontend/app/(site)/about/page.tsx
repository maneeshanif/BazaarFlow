import type { Metadata } from "next";
import { BrandImage } from "@/components/brand/BrandImage";
import { TapeStrip } from "@/components/brand/TapeStrip";
import { TiltFrame } from "@/components/brand/TiltFrame";
import { ClosingPanel } from "@/components/site/ClosingPanel";
import { Bob, Drift } from "@/components/site/motion";
import { SubHero } from "@/components/site/SubHero";
import { TabCards } from "@/components/site/TabCards";
import { CharText, WordText } from "@/components/site/text";
import { WaveBand } from "@/components/site/WaveBand";

export const metadata: Metadata = {
  title: "About - BazaarFlow",
  description: "BazaarFlow is a back-office for shops in Pakistan that pack and send out orders: sales, stock and customers' udhaar kept straight, with you approving every change.",
};

const FOR = [
  ["Corner grocery and general stores", "Rice, flour and tea sold by the bag, with a page of udhaar for the regulars.", "photo-small-goods.jpg"],
  ["Bakeries, sweet shops and tiffin kitchens", "Boxes packed to order, sent out before noon, paid in cash or on credit.", "photo-bakery-box.jpg"],
  ["Parcel and small-goods sellers", "A few parcels a day to the next street or the next city, each one written down.", "photo-parcels.jpg"],
] as const;

export default function AboutPage() {
  return (
    <>
      <SubHero
        chip="About"
        lines={["Small shops,", "big orders."]}
        lead="BazaarFlow is a back-office for shops in Pakistan that pack and send out orders. You say what happened, and the books follow."
      />

      {/* what we wanted it to be: a sentence on a wave, four tabs under it */}
      <section aria-labelledby="want-title" style={{ zIndex: 90 }} className="paper-forest relative -mt-16 overflow-hidden bg-forest-deep px-4 pb-24 pt-32 md:px-8">
        <h2 id="want-title" className="sr-only">
          What we wanted it to be
        </h2>
        <WaveBand text="We wanted it to be plain, careful and yours." ribbon={false} letters="fill-lime" className="relative h-56 md:h-80" zIndex={1} />
        <TabCards />
      </section>

      {/* a torn paper statement */}
      <section aria-labelledby="idea-title" style={{ zIndex: 80 }} className="paper-lime seam-arc relative -mt-12 px-4 pb-32 pt-36 text-forest-ink md:px-8">
        <div className="mx-auto grid max-w-[110rem] items-center gap-12 lg:grid-cols-[6fr_4fr]">
          <Drift distance={30}>
            <div className="paper-cream relative p-8 shadow-card [clip-path:polygon(0_3%,6%_0,14%_2%,24%_0,36%_2%,48%_0,60%_2%,72%_0,84%_2%,94%_0,100%_3%,100%_97%,92%_100%,80%_98%,66%_100%,52%_98%,40%_100%,26%_98%,12%_100%,0_97%)] md:p-14">
              <TapeStrip className="-top-1 left-10 h-9 w-32 -rotate-3" />
              <CharText id="idea-title" text="To keep a small shop's books without the bookkeeping." className="font-display text-display-lg uppercase leading-[0.95]" />
              <WordText
                text="A shopkeeper already knows what happened: two shirts to Ali, Rs 2,000 from Sana, a box of sweets sent out. BazaarFlow takes that sentence and does the sums, the stock and the ledger, then waits for your yes."
                className="mt-6 max-w-prose text-ui-lg font-medium"
              />
            </div>
          </Drift>
          <Bob amount={18} seconds={4.5} className="mx-auto w-full max-w-sm">
            <TiltFrame tilt={5} className="aspect-[3/4]">
              <BrandImage file="photo-shop-counter.jpg" alt="A shopkeeper at the counter writing an order into a phone" label="Shop counter" tone="sunny" />
            </TiltFrame>
          </Bob>
        </div>
      </section>

      {/* who it is for */}
      <section aria-labelledby="for-title" style={{ zIndex: 70 }} className="paper-forest relative -mt-12 overflow-hidden bg-forest px-4 pb-28 pt-32 md:px-8">
        <div className="mx-auto max-w-[110rem]">
          <CharText id="for-title" text="Who it is for." className="text-display-lg uppercase text-lime" />
          <ul className="mt-12 grid gap-6 md:grid-cols-3">
            {FOR.map(([title, text, photo], i) => (
              <li key={title}>
                <Bob amount={10 + i * 4} seconds={4 + i * 0.5}>
                  <div className="overflow-hidden rounded-card bg-cream text-forest-ink shadow-card">
                    <div className="aspect-[4/3]">
                      <BrandImage file={photo} alt="" decorative label={title} tone={i === 0 ? "coral" : i === 1 ? "sunny" : "sky"} />
                    </div>
                    <div className="p-6">
                      <h3 className="font-display text-ui-2xl uppercase">{title}</h3>
                      <p className="mt-2 text-ui-base font-medium">{text}</p>
                    </div>
                  </div>
                </Bob>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <ClosingPanel zIndex={60} />
    </>
  );
}
