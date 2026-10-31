import type { Metadata } from "next";
import Link from "next/link";
import { BrandImage } from "@/components/brand/BrandImage";
import { Cursor } from "@/components/site/Cursor";
import { FooterPile } from "@/components/site/FooterPile";
import { Intro } from "@/components/site/Intro";
import { MenuTab, type MenuLink } from "@/components/site/MenuTab";
import { SiteScroll } from "@/components/site/SiteScroll";

export const metadata: Metadata = {
  title: "BazaarFlow - the back-office that keeps your khata",
  description:
    "Tell BazaarFlow what you sold in English or Roman Urdu. It updates your stock and your customers' udhaar, and nothing changes until you approve it.",
};

/** The pull-tab menu. Same destinations the header and footer always had, plus the sign-up. */
const MENU: MenuLink[] = [
  { label: "How it works", href: "/#how" },
  { label: "You stay in charge", href: "/#control" },
  { label: "Live demo", href: "/demo" },
  { label: "Create your shop", href: "/register" },
  { label: "Sign in", href: "/sign-in" },
];

/** Footer labels sit across the top of the dark board, each with a lime dot beneath (as on the reference). */
const FOOT_LINK =
  "group relative pb-3 font-display text-ui-2xl uppercase tracking-wide text-lime focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-lime after:absolute after:bottom-0 after:left-1/2 after:h-2 after:w-2 after:-translate-x-1/2 after:rounded-full after:bg-lime after:transition-transform hover:after:scale-[2.2]";

/** Chrome of the public site (landing, live demo). The signed-in application has its own shell. */
export default function SiteLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="min-h-screen bg-forest-deep text-cream">
      <Intro />
      <Cursor />
      <SiteScroll />
      <a href="#content" className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-[160] focus:rounded-pill focus:bg-forest focus:px-4 focus:py-2 focus:text-lime">
        Skip to the content
      </a>
      <header className="absolute inset-x-0 top-0 z-[120]">
        <div className="mx-auto flex max-w-[110rem] items-start justify-between gap-4 px-4 py-4 md:px-8">
          <Link href="/" aria-label="BazaarFlow home" className="flex h-12 w-28 overflow-hidden rounded-chip focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-line-focus">
            <BrandImage file="logo-badge.png" alt="BazaarFlow" label="BazaarFlow" tone="forest" />
          </Link>
        </div>
      </header>
      <MenuTab links={MENU} />

      <main id="content">{children}</main>

      <footer className="paper-forest relative -mt-12 overflow-hidden bg-forest">
        <nav aria-label="Footer" className="mx-auto flex max-w-[110rem] flex-wrap justify-between gap-x-8 gap-y-4 px-4 pt-28 md:px-8">
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
        <div className="relative mx-auto flex min-h-[32rem] max-w-[110rem] flex-col items-center justify-center px-4 py-24 text-center">
          <div className="h-16 w-28 -rotate-3 overflow-hidden rounded-chip" aria-hidden>
            <BrandImage file="logo-badge.png" alt="" decorative label="BazaarFlow" tone="lime" />
          </div>
          <p className="mt-4 font-display text-display-xl uppercase leading-[0.9] text-lime">
            Bazaar
            <br />
            by you
          </p>
          <p className="mt-6 max-w-md text-ui-md text-cream">A back-office for shops in Pakistan. Coming next: orders from WhatsApp and posts to Facebook.</p>
          <FooterPile />
        </div>
        <p className="relative pb-6 text-center text-ui-sm text-cream/80">&copy; {new Date().getFullYear()} BazaarFlow</p>
      </footer>
    </div>
  );
}
