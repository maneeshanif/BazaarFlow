import type { Metadata } from "next";
import Link from "next/link";
import { BrandImage } from "@/components/brand/BrandImage";
import { Intro } from "@/components/site/Intro";
import { RollAcross } from "@/components/site/motion";
import { SITE_PRIMARY } from "@/components/site/styles";

export const metadata: Metadata = {
  title: "BazaarFlow - the back-office that keeps your khata",
  description:
    "Tell BazaarFlow what you sold in English or Roman Urdu. It updates your stock and your customers' udhaar, and nothing changes until you approve it.",
};

const LINK =
  "rounded-pill px-4 py-2 font-display text-ui-lg uppercase tracking-wide text-forest-ink hover:bg-forest hover:text-lime focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-line-focus";

const FOOT_LINK =
  "font-display text-ui-2xl uppercase tracking-wide text-lime hover:underline hover:decoration-dotted hover:underline-offset-8 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-lime";

const ROLLS = [
  { file: "roll-sales.png", label: "Sales", tone: "coral", at: "left-[4%] top-[48%]" },
  { file: "roll-stock.png", label: "Stock", tone: "sunny", at: "left-[24%] top-[70%]" },
  { file: "roll-chat.png", label: "Chat", tone: "orange", at: "right-[26%] top-[62%]" },
  { file: "roll-money.png", label: "Money", tone: "sky", at: "right-[4%] top-[72%]" },
] as const;

/** Chrome of the public site (landing, live demo). The signed-in application has its own shell. */
export default function SiteLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="min-h-screen bg-forest-deep text-cream">
      <Intro />
      <a href="#content" className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded-pill focus:bg-forest focus:px-4 focus:py-2 focus:text-lime">
        Skip to the content
      </a>
      <header className="absolute inset-x-0 top-0 z-40">
        <div className="mx-auto flex max-w-[110rem] items-center justify-between gap-4 px-4 py-5 md:px-8">
          <Link href="/" aria-label="BazaarFlow home" className="flex h-12 w-28 overflow-hidden rounded-chip focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-line-focus">
            <BrandImage file="logo-badge.png" alt="BazaarFlow" label="BazaarFlow" tone="forest" />
          </Link>
          <nav aria-label="Main" className="flex items-center gap-1">
            <Link href="/#how" className={`${LINK} hidden md:inline`}>
              How it works
            </Link>
            <Link href="/#control" className={`${LINK} hidden md:inline`}>
              You stay in charge
            </Link>
            <Link href="/sign-in" className={LINK}>
              Sign in
            </Link>
            <Link href="/demo" className={`${SITE_PRIMARY} ml-2 min-h-control-md px-5 text-ui-base`}>
              Live demo
            </Link>
          </nav>
        </div>
      </header>

      <main id="content">{children}</main>

      <footer className="paper-forest relative -mt-12 overflow-hidden bg-forest">
        <div className="mx-auto flex max-w-[110rem] flex-wrap justify-between gap-x-8 gap-y-3 px-4 pt-28 md:px-8">
          <nav aria-label="Footer" className="contents">
            <Link href="/#how" className={FOOT_LINK}>
              How it works
            </Link>
            <Link href="/demo" className={FOOT_LINK}>
              Live demo
            </Link>
            <Link href="/register" className={FOOT_LINK}>
              Create your shop
            </Link>
            <Link href="/sign-in" className={FOOT_LINK}>
              Sign in
            </Link>
          </nav>
        </div>
        <div className="relative mx-auto flex min-h-[28rem] max-w-[110rem] flex-col items-center justify-center px-4 py-24 text-center">
          <p className="font-display text-display-xl uppercase leading-[0.9] text-lime">
            Bazaar
            <br />
            by you
          </p>
          <p className="mt-6 max-w-md text-ui-md text-cream">A back-office for shops in Pakistan. Coming next: orders from WhatsApp and posts to Facebook.</p>
          {ROLLS.map((r) => (
            <RollAcross key={r.file} from={0} to={0} spins={1} className={`absolute hidden h-28 w-28 overflow-hidden rounded-full md:block ${r.at}`}>
              <BrandImage file={r.file} alt="" decorative label={r.label} tone={r.tone} />
            </RollAcross>
          ))}
        </div>
        <p className="relative pb-6 text-center text-ui-sm text-cream/80">&copy; {new Date().getFullYear()} BazaarFlow</p>
      </footer>
    </div>
  );
}
