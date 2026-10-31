import type { Metadata } from "next";
import { ClosingPanel } from "@/components/site/ClosingPanel";
import { NewsList, type NewsItem } from "@/components/site/NewsList";
import { SubHero } from "@/components/site/SubHero";

export const metadata: Metadata = {
  title: "News - BazaarFlow",
  description: "What has shipped in BazaarFlow and what is coming next.",
};

/** Product notes. Add the newest first. Only things that exist, or are plainly marked as coming next. */
const ITEMS: NewsItem[] = [
  {
    id: "look",
    kind: "Update",
    title: "A new look, top to bottom",
    text: "The public site, the sign-in pages and every screen of the app share one identity now: paper, curves and big type.",
    when: "Oct 2026",
    photo: "photo-family.jpg",
    tone: "sunny",
    href: "/how-it-works",
  },
  {
    id: "demo",
    kind: "Update",
    title: "A private demo shop for a day",
    text: "One click opens a shop of your own with sales, products and customers already in it. No sign-up.",
    when: "Oct 2026",
    photo: "photo-shop-counter.jpg",
    tone: "coral",
    href: "/demo",
  },
  {
    id: "urdu",
    kind: "Update",
    title: "Say it in Roman Urdu",
    text: "The sales chat understands English and Roman Urdu, and every change waits for a manager to approve it.",
    when: "Oct 2026",
    photo: "photo-ledger.jpg",
    tone: "indigo",
    href: "/features#sales",
  },
  {
    id: "whatsapp",
    kind: "Next",
    title: "Orders from WhatsApp",
    text: "Customer messages arriving in the inbox next to their orders. Waits for the shop's WhatsApp account to be connected.",
    when: "Coming",
    photo: "photo-delivery-bag.jpg",
    tone: "sky",
    href: "/features#inbox",
  },
  {
    id: "facebook",
    kind: "Next",
    title: "Posts to your Facebook Page",
    text: "Drafts you approve are already written. Publishing them waits for your Page to be connected.",
    when: "Coming",
    photo: "photo-market.jpg",
    tone: "orange",
    href: "/features#marketing",
  },
  {
    id: "voice",
    kind: "Next",
    title: "Support calls by voice",
    text: "A voice assistant that answers questions about your shop. The call screen is built; the voice service is being connected.",
    when: "Coming",
    photo: "photo-doorstep.jpg",
    tone: "lime",
  },
];

export default function NewsPage() {
  return (
    <>
      <SubHero chip="News" lines={["What's", "rolling."]} lead="What has shipped, and what is coming next, newest first." />
      <section aria-label="Product notes" style={{ zIndex: 90 }} className="paper-forest relative -mt-16 overflow-hidden bg-forest-deep px-4 pb-32 pt-40 md:px-8">
        <NewsList items={ITEMS} />
      </section>
      <ClosingPanel zIndex={70} />
    </>
  );
}
