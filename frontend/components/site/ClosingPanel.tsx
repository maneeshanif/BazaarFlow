import Link from "next/link";
import { BrandImage } from "@/components/brand/BrandImage";
import { TiltFrame } from "@/components/brand/TiltFrame";
import { BrandVideo } from "@/components/site/BrandVideo";
import { SITE_ON_FOREST, SITE_ON_FOREST_SECONDARY } from "@/components/site/styles";
import { StartDemoButton } from "@/components/site/StartDemoButton";
import { CharText, RollLabel } from "@/components/site/text";

/** The closing panel every public page ends with: a taped photo and a dark rounded panel with the two ways in. */
export function ClosingPanel({ zIndex = 65 }: { zIndex?: number }) {
  return (
    <section aria-labelledby="try-title" style={{ zIndex }} className="paper-lime seam-arc-top seam-arc relative -mt-12 px-4 pb-28 pt-32 text-forest-ink md:px-8">
      <div className="mx-auto grid max-w-[110rem] gap-6 lg:grid-cols-2">
        <TiltFrame tilt={-3} className="min-h-[22rem]">
          <BrandVideo name="story-handover" fallback={<BrandImage file="photo-handover.jpg" alt="" decorative label="The handover" tone="sunny" />} className="object-cover" />
        </TiltFrame>
        <div className="rounded-card bg-forest p-8 text-cream shadow-card md:p-14">
          <CharText id="try-title" text="Let's get every order there." className="text-display-lg text-lime" />
          <p className="mt-5 max-w-prose text-ui-lg">A day of sales, eight products and three customers are waiting. Make a sale by chat and approve it yourself.</p>
          <div className="mt-8 flex flex-wrap items-start gap-3">
            <StartDemoButton className={SITE_ON_FOREST}>Try the live demo</StartDemoButton>
            <Link href="/register" className={SITE_ON_FOREST_SECONDARY}>
              <RollLabel text="Create your shop" />
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
