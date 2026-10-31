"use client";

import { gsap } from "gsap";
import { useLayoutEffect, useRef, type ReactNode } from "react";
import { BrandImage } from "@/components/brand/BrandImage";
import { Chip } from "@/components/brand/Chip";
import { TiltFrame } from "@/components/brand/TiltFrame";
import { Bob, register } from "@/components/site/motion";

function Note({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p aria-hidden className={`font-slip text-ui-lg leading-tight text-forest-ink ${className ?? ""}`}>
      {children}
    </p>
  );
}

function Count({ n }: { n: number }) {
  return (
    <span aria-hidden className="grid h-12 w-12 place-items-center rounded-full border-2 border-forest-ink font-slip text-ui-xl text-forest-ink">
      {n}
    </span>
  );
}

function Word({ n, children }: { n: number; children: string }) {
  return (
    <div className="flex shrink-0 items-start gap-3">
      <Count n={n} />
      <p className="giant-word font-display uppercase text-forest-ink">{children}</p>
    </div>
  );
}

function Disc({ file, label, className }: { file: string; label: string; className?: string }) {
  return (
    <Bob amount={22} seconds={3.4} className={`aspect-square w-32 shrink-0 md:w-44 ${className ?? ""}`}>
      <div className="h-full w-full -rotate-6 overflow-hidden rounded-full shadow-card">
        <BrandImage file={file} alt="" decorative label={label} tone="cream" />
      </div>
    </Bob>
  );
}

function Photo({ file, label, tilt, alt, className }: { file: string; label: string; tilt: -8 | -5 | 5 | 8; alt: string; className?: string }) {
  return (
    <Bob amount={26} seconds={4.2} className={`w-48 shrink-0 md:w-64 ${className ?? ""}`}>
      <TiltFrame tilt={tilt} className="aspect-[3/4]">
        <BrandImage file={file} alt={alt} label={label} tone="forest" />
      </TiltFrame>
    </Bob>
  );
}

/**
 * The reference's longest scene: the screen stays put while one very long line of huge words slides across it, with
 * photos, round discs and handwritten notes bobbing up and down at their own pace between the words. On a phone, or when
 * motion is reduced, nothing is pinned and the same pieces simply stack.
 */
export function GiantStory() {
  const wrap = useRef<HTMLDivElement | null>(null);
  const track = useRef<HTMLDivElement | null>(null);
  useLayoutEffect(() => {
    if (!wrap.current || !track.current) return;
    register();
    const mm = gsap.matchMedia();
    mm.add("(min-width: 768px) and (prefers-reduced-motion: no-preference)", () => {
      const el = track.current!;
      el.dataset.mode = "h";
      const dist = () => Math.max(0, el.scrollWidth - window.innerWidth);
      gsap.to(el, {
        x: () => -dist(),
        ease: "none",
        scrollTrigger: { trigger: wrap.current, pin: true, scrub: 0.6, start: "top top", end: () => `+=${dist()}`, invalidateOnRefresh: true, anticipatePin: 1 },
      });
      return () => {
        delete el.dataset.mode;
      };
    });
    return () => mm.revert();
  }, []);
  return (
    <section aria-labelledby="why-title" style={{ zIndex: 75 }} className="paper-lime seam-arc relative -mt-12 bg-lime text-forest-ink">
      <div ref={wrap} className="overflow-hidden px-4 py-24 md:flex md:h-screen md:items-center md:px-0 md:py-0">
        <div ref={track} className="giant-track flex flex-col items-start gap-16 md:gap-[8vw] md:ps-[8vw] md:pe-[10vw]">
          <div className="max-w-xl shrink-0">
            <Chip>Why we exist</Chip>
            <h2 id="why-title" className="mt-5 font-display text-display-lg uppercase leading-[0.95]">
              We&apos;re here for the everyday orders.
            </h2>
            <p className="mt-5 max-w-prose text-ui-lg font-medium">The parcel to the next street, the tiffin before noon, the bag of rice on credit. Small orders, every day, kept straight.</p>
          </div>

          <Word n={1}>To count</Word>
          <Photo file="photo-small-goods.jpg" label="Small goods" tilt={-5} alt="A shelf of small goods in a corner shop" />
          <div className="relative shrink-0">
            <Disc file="disc-stock.png" label="Stock" />
            <Note className="mt-3 max-w-[10rem]">every shelf, counted once</Note>
          </div>

          <Word n={2}>To pack</Word>
          <Photo file="photo-bakery-box.jpg" label="Bakery box" tilt={5} alt="A baker tying twine around a small bakery box" />
          <Disc file="disc-sales.png" label="Sales" />
          <Photo file="photo-doorstep.jpg" label="Doorstep" tilt={-8} alt="A parcel and a bag of groceries on a doorstep" />
          <Note className="max-w-[11rem] shrink-0">from our hands to theirs, arriving whole</Note>

          <Word n={3}>To settle up</Word>
          <Photo file="photo-ledger.jpg" label="Ledger" tilt={5} alt="A hand writing in a khata ledger" />
          <Disc file="disc-khata.png" label="Khata" />
        </div>
      </div>
    </section>
  );
}
