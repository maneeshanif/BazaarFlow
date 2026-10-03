import Link from "next/link";
import { SITE_SECONDARY } from "@/components/site/styles";
import { StartDemoButton } from "@/components/site/StartDemoButton";

export const metadata = { title: "Live demo - BazaarFlow" };

const STEPS = [
  "Open your own shop. It is already stocked: eight products, three customers and a week of sales.",
  "Open Sales chat and write: sell 1 cotton shirt to ali. Then say yes.",
  "Open Approvals, read the card and approve it. Stock, the order and Ali's udhaar change together.",
];

/** Public live demo (PRD F-027): a temporary shop per visitor, deleted after 24 hours. */
export default function DemoPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-14 md:px-6 md:py-20">
      <h1 className="font-display text-display-lg text-ink">Run a shop for five minutes.</h1>
      <p className="mt-4 max-w-prose text-ui-lg text-ink-soft">
        You get a private shop that only you can see. Change anything: it is deleted after 24 hours and never touches a real shop.
      </p>
      <ol className="mt-8 flex max-w-prose flex-col gap-4 border-t border-ledger-rule pt-6 text-ui-base text-ink">
        {STEPS.map((step) => (
          <li key={step} className="border-l-2 border-ink pl-4">
            {step}
          </li>
        ))}
      </ol>
      <div className="mt-8 flex flex-wrap items-start gap-3">
        <StartDemoButton>Open my demo shop</StartDemoButton>
        <Link href="/register" className={SITE_SECONDARY}>
          Create your own shop instead
        </Link>
      </div>
      <p className="mt-4 max-w-prose text-ui-sm text-ink-soft">
        The AI assistant in the demo has a small allowance of its own. If it runs out, you can still record sales by hand.
      </p>
    </div>
  );
}
