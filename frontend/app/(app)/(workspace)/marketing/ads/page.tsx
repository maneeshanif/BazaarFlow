"use client";

import Link from "next/link";
import { PageHeader } from "@/components/app/PageHeader";
import { RequireRole } from "@/components/app/RequireRole";

const STEPS = [
  "The agent proposes a campaign for a product or an offer: the picture, the words, the audience and a daily budget.",
  "You approve it. Nothing is paid for or published until you do.",
  "It reports what each campaign cost and what it brought in, next to your orders.",
];

/** The Facebook ads agent. Not built yet: it waits for a connected Facebook account, so this page says so instead of faking a screen. */
export default function AdsAgentPage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <div className="flex flex-col gap-4">
        <PageHeader title="Facebook ads agent" description="Coming next, once your Facebook account is connected." />
        <section aria-label="How it will work" className="flex flex-col gap-3 rounded-card border-2 border-line-strong bg-surface-raised p-6 shadow-card">
          <h2 className="text-ui-md font-semibold text-fg">How it will work</h2>
          <ol className="flex max-w-prose list-decimal flex-col gap-2 ps-5 text-ui-sm text-fg-muted">
            {STEPS.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ol>
          <Link href="/marketing" className="text-ui-sm font-medium text-action hover:underline">
            Meanwhile, use the marketing agent
          </Link>
        </section>
      </div>
    </RequireRole>
  );
}
