import type { Metadata } from "next";
import { JetBrains_Mono, Young_Serif } from "next/font/google";
import Link from "next/link";
import { SITE_PRIMARY } from "@/components/site/styles";

const display = Young_Serif({ subsets: ["latin"], weight: "400", variable: "--font-display", display: "swap" });
const slip = JetBrains_Mono({ subsets: ["latin"], variable: "--font-slip", display: "swap" });

export const metadata: Metadata = {
  title: "BazaarFlow - the back-office that keeps your khata",
  description:
    "Tell BazaarFlow what you sold in English or Roman Urdu. It updates your stock and your customers' udhaar, and nothing changes until you approve it.",
};

const LINK =
  "rounded-md px-2 py-1 text-ui-base text-ink hover:bg-ledger-rule/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-focus";

/** Chrome of the public site (landing, live demo). The signed-in application has its own shell. */
export default function SiteLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className={`${display.variable} ${slip.variable} min-h-screen bg-ledger text-ink`}>
      <a href="#content" className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:rounded-md focus:bg-ink focus:px-3 focus:py-2 focus:text-fg-inverse">
        Skip to the content
      </a>
      <header className="border-b border-ledger-rule">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 md:px-6">
          <Link href="/" className="font-display text-ui-xl text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-focus">
            BazaarFlow
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
            <Link href="/demo" className={`${SITE_PRIMARY} ml-2 min-h-control-md px-3 text-ui-base`}>
              Live demo
            </Link>
          </nav>
        </div>
      </header>

      <main id="content">{children}</main>

      <footer className="mt-24 border-t border-ledger-rule">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-ui-sm text-ink-soft md:flex-row md:items-start md:justify-between md:px-6">
          <div className="max-w-sm">
            <p className="font-display text-ui-lg text-ink">BazaarFlow</p>
            <p className="mt-1">A back-office for shops in Pakistan. Coming next: orders from WhatsApp and posts to Facebook.</p>
          </div>
          <nav aria-label="Footer" className="flex flex-wrap gap-x-5 gap-y-2">
            <Link href="/demo" className="underline underline-offset-4 hover:text-ink">
              Live demo
            </Link>
            <Link href="/register" className="underline underline-offset-4 hover:text-ink">
              Create your shop
            </Link>
            <Link href="/sign-in" className="underline underline-offset-4 hover:text-ink">
              Sign in
            </Link>
          </nav>
          <p>&copy; {new Date().getFullYear()} BazaarFlow</p>
        </div>
      </footer>
    </div>
  );
}
