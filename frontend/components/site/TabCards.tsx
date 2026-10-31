"use client";

import { ShieldCheck, Smartphone, Store, Type, type LucideIcon } from "lucide-react";
import { Bob } from "@/components/site/motion";

type Card = { n: string; label: string; text: string; icon: LucideIcon; tone: string; at: string };

const CARDS: Card[] = [
  { n: "01", label: "Plain", text: "Rupees, udhaar and short words, not accounting terms.", icon: Type, tone: "bg-indigo text-cream", at: "md:left-[6%] md:top-0" },
  { n: "02", label: "Approved", text: "Nothing changes until a manager or the owner says yes.", icon: ShieldCheck, tone: "bg-lime text-forest-ink", at: "md:left-[34%] md:top-16" },
  { n: "03", label: "Yours", text: "One shop never sees another shop's data.", icon: Store, tone: "bg-sunny text-forest-ink", at: "md:left-[62%] md:top-0" },
  { n: "04", label: "On a phone", text: "Every screen works at 360 px, because the counter is not a desk.", icon: Smartphone, tone: "bg-coral text-forest-ink", at: "md:left-[80%] md:top-20" },
];

/**
 * Four rounded "tabs" that float at different heights (the reference's About page does the same with its four ideas).
 * On a phone they stack. Each bobs at its own pace.
 */
export function TabCards() {
  return (
    <ul className="relative mx-auto mt-12 grid max-w-[110rem] gap-6 sm:grid-cols-2 md:block md:h-[26rem]">
      {CARDS.map((c, i) => (
        <li key={c.label} className={`md:absolute md:w-[15rem] ${c.at}`}>
          <Bob amount={14 + i * 3} seconds={3 + i * 0.6}>
            <div className={`rounded-card p-5 shadow-card ${c.tone}`} style={{ transform: `rotate(${i % 2 ? 3 : -3}deg)` }}>
              <div className="flex items-center justify-between">
                <span className="font-slip text-ui-sm">{c.n}</span>
                <c.icon aria-hidden className="h-6 w-6" />
              </div>
              <h3 className="mt-3 font-display text-ui-2xl uppercase">{c.label}</h3>
              <p className="mt-1 text-ui-base font-medium">{c.text}</p>
            </div>
          </Bob>
        </li>
      ))}
    </ul>
  );
}
