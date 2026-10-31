import type { Metadata } from "next";
import { TapeStrip } from "@/components/brand/TapeStrip";
import { CONTACT_EMAIL } from "@/components/site/content";
import { ContactForm } from "@/components/site/ContactForm";
import { Bob } from "@/components/site/motion";
import { SubHero } from "@/components/site/SubHero";
import { CharText } from "@/components/site/text";

export const metadata: Metadata = {
  title: "Contact - BazaarFlow",
  description: "Write to the BazaarFlow team about your shop.",
};

export default function ContactPage() {
  return (
    <SubHero chip="Get in touch" lines={["Let's talk", "shop."]} lead="Tell us about your shop and what you send out. We read every message.">
      {/* the form sits on a cream panel with a dotted top edge, the sticky note leans on its corner */}
      <div className="relative mx-auto mt-12 w-full max-w-5xl">
        <div className="paper-cream relative rounded-card px-6 pb-10 pt-12 text-forest-ink shadow-card md:px-12">
          <span aria-hidden className="absolute inset-x-6 top-4 border-t-4 border-dotted border-lime" />
          <CharText text="Drop us a message" className="mb-6 font-display text-ui-3xl uppercase leading-none" />
          <ContactForm />
        </div>
        <Bob amount={10} seconds={4} className="absolute -top-10 right-2 w-60 rotate-[6deg] md:-right-16">
          <div className="relative rounded-chip bg-sunny p-5 text-forest-ink shadow-card">
            <TapeStrip className="-top-3 left-1/2 h-8 w-24 -translate-x-1/2 -rotate-3" />
            <p className="font-display text-ui-sm uppercase tracking-widest">Email</p>
            <a href={`mailto:${CONTACT_EMAIL}`} className="roll mt-1 block break-all font-slip text-ui-lg underline decoration-dotted underline-offset-4 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-line-focus">
              {CONTACT_EMAIL}
            </a>
          </div>
        </Bob>
      </div>
    </SubHero>
  );
}
