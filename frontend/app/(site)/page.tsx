import Link from "next/link";
import { HeroSlip } from "@/components/site/HeroSlip";
import { SITE_SECONDARY } from "@/components/site/styles";
import { StartDemoButton } from "@/components/site/StartDemoButton";

const ROWS = [
  {
    say: "2 shirt bech do Ali ko",
    does: "Writes the sale, takes 2 shirts off the shelf and adds Rs 5,000 to Ali's udhaar, once a manager approves it.",
  },
  {
    say: "Ali ne 2000 diye",
    does: "Records Rs 2,000 from Ali and shows what he still owes.",
  },
  {
    say: "What did I sell today?",
    does: "Answers from your own sales: the total, the number of orders, and the profit if you are an owner or manager.",
  },
  {
    say: "Write an Eid offer post",
    does: "Drafts it in your tone. You edit it and send it for approval. Publishing to Facebook comes later.",
  },
];

const CONTROLS = [
  "Sales, payments and stock changes wait for a manager or the owner to approve them.",
  "Every conversation is logged with the tools it used. Names, phone numbers and emails are hidden in the log.",
  "The owner can pause the assistant at any moment, and each shop has a monthly AI allowance that stops it.",
  "Staff can chat and propose. Only owners and managers approve.",
];

const BAZAAR = [
  ["Rupees and udhaar", "Prices in Rs, and a ledger for each customer with their purchases and payments."],
  ["English and Roman Urdu", "Write the way you talk. The assistant understands both."],
  ["Made for a phone", "Every screen works at 360 px wide, because the counter is not a desk."],
  ["Your shop is yours", "One shop never sees another shop's data. Each demo is a private shop of its own."],
];

/** Public landing page (PRD F-026). */
export default function LandingPage() {
  return (
    <>
      <section className="mx-auto grid max-w-6xl gap-10 px-4 pb-16 pt-12 md:px-6 md:pt-20 lg:grid-cols-[6fr_5fr] lg:items-center">
        <div>
          <h1 className="max-w-[18ch] font-display text-display-xl text-ink">Tell it what you sold. It keeps the khata.</h1>
          <p className="mt-5 max-w-prose text-ui-lg text-ink-soft">
            BazaarFlow is a back-office for shops in Pakistan. Write a sale in English or Roman Urdu and it updates your stock and your customers&apos; udhaar.
            Nothing changes until you approve it.
          </p>
          <div className="mt-7 flex flex-wrap items-start gap-3">
            <StartDemoButton />
            <Link href="/register" className={SITE_SECONDARY}>
              Create your shop
            </Link>
          </div>
          <p className="mt-3 max-w-prose text-ui-sm text-ink-soft">Free. The demo gives you a shop of your own for a day, with sales and customers already in it. No sign-up.</p>
        </div>
        <HeroSlip />
      </section>

      <section id="how" aria-labelledby="how-title" className="mx-auto max-w-6xl scroll-mt-6 px-4 py-14 md:px-6">
        <h2 id="how-title" className="max-w-[24ch] font-display text-display-lg text-ink">
          Say it the way you would say it to a helper.
        </h2>
        <dl className="mt-8 border-t border-ledger-rule">
          {ROWS.map((row) => (
            <div key={row.say} className="grid gap-1 border-b border-ledger-rule py-4 md:grid-cols-[2fr_3fr] md:gap-8">
              <dt className="font-slip text-ui-base text-ink">&ldquo;{row.say}&rdquo;</dt>
              <dd className="max-w-prose text-ui-base text-ink-soft">{row.does}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section id="control" aria-labelledby="control-title" className="mx-auto grid max-w-6xl scroll-mt-6 gap-10 px-4 py-14 md:px-6 lg:grid-cols-[4fr_6fr] lg:items-center">
        <div className="flex justify-start lg:justify-center" aria-hidden="true">
          <div className="-rotate-[7deg] rounded-md border-4 border-stamp px-6 py-3 font-display text-ui-3xl tracking-wide text-stamp mix-blend-multiply">APPROVED</div>
        </div>
        <div>
          <h2 id="control-title" className="max-w-[22ch] font-display text-display-lg text-ink">
            You stay in charge of your shop.
          </h2>
          <ul className="mt-6 flex max-w-prose flex-col gap-3 text-ui-base text-ink-soft">
            {CONTROLS.map((c) => (
              <li key={c} className="border-l-2 border-stamp pl-4">
                {c}
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section aria-labelledby="bazaar-title" className="mx-auto max-w-6xl px-4 py-14 md:px-6">
        <h2 id="bazaar-title" className="max-w-[24ch] font-display text-display-lg text-ink">
          Built for how a bazaar shop works.
        </h2>
        <ul className="mt-8 grid gap-x-10 gap-y-6 md:grid-cols-2">
          {BAZAAR.map(([title, text]) => (
            <li key={title} className="max-w-prose">
              <h3 className="text-ui-lg font-semibold text-ink">{title}</h3>
              <p className="mt-1 text-ui-base text-ink-soft">{text}</p>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="try-title" className="mx-auto max-w-6xl px-4 pt-6 md:px-6">
        <div className="rounded-lg bg-ink p-8 text-fg-inverse md:p-12">
          <h2 id="try-title" className="max-w-[20ch] font-display text-display-lg">
            See it in a shop that is already running.
          </h2>
          <p className="mt-3 max-w-prose text-ui-md text-ledger-rule">A day of sales, eight products and three customers are waiting. Make a sale by chat and approve it yourself.</p>
          <div className="mt-6 flex flex-wrap items-start gap-3">
            <StartDemoButton className="bg-ledger text-ink hover:bg-ledger-raised">Try the live demo</StartDemoButton>
            <Link href="/register" className="inline-flex min-h-control-lg items-center rounded-md border border-ledger-rule px-5 text-ui-md font-semibold text-fg-inverse hover:bg-ink-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-focus">
              Create your shop
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
