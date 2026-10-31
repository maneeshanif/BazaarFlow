"use client";

import { gsap } from "gsap";
import { useLayoutEffect, useRef, type CSSProperties, type ReactNode } from "react";
import { BrandImage } from "@/components/brand/BrandImage";
import { Chip } from "@/components/brand/Chip";
import { TiltFrame } from "@/components/brand/TiltFrame";
import { Bob, register } from "@/components/site/motion";
import { CharText, WordText } from "@/components/site/text";

/** Where a piece sits on the big stage, in viewport widths and heights. Ignored when the pieces stack. */
type At = { l: number; t: number; depth?: number };
const pos = ({ l, t, depth = 1 }: At) => ({ "--l": `${l}vw`, "--t": `${t}vh`, "--d": depth }) as CSSProperties;

/** A piece on the stage. `depth` above 1 slides past faster than the words, below 1 slower, so the scene has layers. */
function Piece({ at, children, word }: { at: At; children: ReactNode; word?: number }) {
  return (
    <div data-piece data-depth={at.depth ?? 1} data-word={word} style={pos(at)} className="gi shrink-0">
      {children}
    </div>
  );
}

function Count({ n }: { n: number }) {
  return (
    <span aria-hidden className="grid h-12 w-12 shrink-0 place-items-center rounded-full border-2 border-forest-ink font-slip text-ui-xl text-forest-ink md:h-16 md:w-16 md:text-ui-2xl">
      {n}
    </span>
  );
}

function Disc({ file, label }: { file: string; label: string }) {
  return (
    <Bob amount={22} seconds={3.4} className="aspect-square w-32 md:w-[min(14rem,24vh)]">
      <div className="h-full w-full -rotate-6 overflow-hidden rounded-full shadow-card">
        <BrandImage file={file} alt="" decorative label={label} tone="cream" />
      </div>
    </Bob>
  );
}

function Photo({ file, label, tilt, alt }: { file: string; label: string; tilt: -8 | -5 | 5 | 8; alt: string }) {
  return (
    <Bob amount={26} seconds={4.2} className="w-48 md:w-[min(17rem,30vh)]">
      <TiltFrame tilt={tilt} className="aspect-[3/4]">
        <BrandImage file={file} alt={alt} label={label} tone="forest" />
      </TiltFrame>
    </Bob>
  );
}

function Note({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p aria-hidden className={`font-slip text-ui-lg leading-tight text-forest-ink ${className ?? ""}`}>
      {children}
    </p>
  );
}

/** A hand-drawn arrow that draws itself as the camera reaches it. */
function Arrow({ flip }: { flip?: boolean }) {
  return (
    <svg aria-hidden viewBox="0 0 220 120" className={`h-20 w-40 text-forest-ink md:h-28 md:w-56 ${flip ? "-scale-x-100" : ""}`} fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <path data-draw d="M6 100 C 60 20, 140 10, 206 52" />
      <path data-draw d="M186 34 L 207 52 L 182 62" />
    </svg>
  );
}

/**
 * The reference's longest scene. The screen stays put while a camera travels over one big stage: it reads the first word,
 * swings down-right to the second (which enters from below), then up to the third (which enters from above). Photos, round
 * discs and notes sit at different depths so they slide past at different speeds, bob up and down on their own, and the
 * arrows draw themselves as they are reached. On a phone, or with reduced motion, nothing is pinned and the pieces stack.
 */
export function GiantStory() {
  const wrap = useRef<HTMLDivElement | null>(null);
  const stage = useRef<HTMLDivElement | null>(null);
  useLayoutEffect(() => {
    const root = wrap.current;
    const el = stage.current;
    if (!root || !el) return;
    register();
    const mm = gsap.matchMedia();
    mm.add("(min-width: 768px) and (prefers-reduced-motion: no-preference)", () => {
      el.dataset.mode = "h";
      const pieces = [...el.querySelectorAll<HTMLElement>("[data-piece]")];
      const words = [...el.querySelectorAll<HTMLElement>("[data-word-main]")];
      // where the camera must be (stage offset) for each word to sit in the middle of the screen
      const cam = (k: number) => {
        if (k === 0) return { x: 0, y: 0 };
        const stageBox = el.getBoundingClientRect();
        const w = words[k - 1].getBoundingClientRect();
        const baseX = stageBox.left - (gsap.getProperty(el, "x") as number);
        const baseY = stageBox.top - (gsap.getProperty(el, "y") as number);
        return { x: window.innerWidth / 2 - (w.left - baseX + w.width / 2), y: root.clientHeight / 2 - (w.top - baseY + w.height / 2) };
      };
      // freeze the camera positions when the scene is measured, so they do not chase their own movement
      let frozen = [cam(0), cam(1), cam(2), cam(3)];
      const measure = () => {
        gsap.set(el, { x: 0, y: 0 });
        frozen = [cam(0), cam(1), cam(2), cam(3)];
      };
      measure();
      const tl = gsap.timeline({
        defaults: { ease: "power2.inOut" },
        scrollTrigger: {
          trigger: root,
          pin: true,
          scrub: 0.7,
          start: "top top",
          end: () => `+=${Math.round(window.innerHeight * 6)}`,
          invalidateOnRefresh: true,
          anticipatePin: 1,
          onRefreshInit: measure,
        },
      });
      // three moves with a short pause between them
      for (let k = 1; k <= 3; k += 1) {
        const at = (k - 1) * 1.4;
        tl.to(el, { x: () => frozen[k].x, y: () => frozen[k].y, duration: 1 }, at);
        for (const p of pieces) {
          const depth = Number(p.dataset.depth ?? 1);
          if (depth === 1) continue;
          tl.to(p, { x: () => (depth - 1) * frozen[k].x, y: () => (depth - 1) * frozen[k].y * 0.6, duration: 1 }, at);
        }
      }
      // arrows draw themselves, each once the camera is moving toward the word it points at
      el.querySelectorAll<SVGPathElement>("[data-draw]").forEach((path, i) => {
        const len = path.getTotalLength();
        gsap.set(path, { strokeDasharray: len, strokeDashoffset: len });
        tl.to(path, { strokeDashoffset: 0, duration: 0.5, ease: "none" }, Math.floor(i / 2) * 1.4 + 0.2);
      });
      return () => {
        delete el.dataset.mode;
        gsap.set([el, ...pieces], { clearProps: "transform" });
      };
    });
    return () => mm.revert();
  }, []);
  return (
    <section aria-labelledby="why-title" style={{ zIndex: 75 }} className="paper-lime seam-arc relative -mt-12 bg-lime text-forest-ink">
      <div ref={wrap} className="giant-wrap overflow-hidden px-4 py-24">
        <div ref={stage} className="giant-track relative flex flex-col items-start gap-14">
          <Piece at={{ l: 4, t: 22, depth: 1 }}>
            <div className="max-w-xl md:w-[42vw]">
              <Chip>Why we exist</Chip>
              <CharText id="why-title" text="We're here for the everyday orders." className="mt-5 font-display text-display-lg uppercase leading-[0.95]" />
              <WordText text="The parcel to the next street, the tiffin before noon, the bag of rice on credit. Small orders, every day, kept straight." className="mt-5 max-w-prose text-ui-lg font-medium" />
            </div>
          </Piece>

          {/* 1: count */}
          <Piece at={{ l: 54, t: 26 }}>
            <div data-word-main className="flex items-start gap-3">
              <Count n={1} />
              <CharText as="p" text="To count" className="giant-word font-display uppercase text-forest-ink" />
            </div>
          </Piece>
          <Piece at={{ l: 64, t: -6, depth: 1.3 }}>
            <Photo file="photo-small-goods.jpg" label="Small goods" tilt={-5} alt="A shelf of small goods in a corner shop" />
          </Piece>
          <Piece at={{ l: 122, t: 66, depth: 0.8 }}>
            <Disc file="disc-stock.png" label="Stock" />
          </Piece>
          <Piece at={{ l: 100, t: 84, depth: 1.1 }}>
            <Note className="max-w-[10rem]">every shelf, counted once</Note>
          </Piece>
          <Piece at={{ l: 150, t: 38 }}>
            <Arrow />
          </Piece>

          {/* 2: pack, enters from below */}
          <Piece at={{ l: 196, t: 78 }}>
            <div data-word-main className="flex items-start gap-3">
              <Count n={2} />
              <CharText as="p" text="To pack" className="giant-word font-display uppercase text-forest-ink" />
            </div>
          </Piece>
          <Piece at={{ l: 176, t: 40, depth: 1.25 }}>
            <Photo file="photo-bakery-box.jpg" label="Bakery box" tilt={5} alt="A baker tying twine around a small bakery box" />
          </Piece>
          <Piece at={{ l: 238, t: 56, depth: 0.82 }}>
            <Disc file="disc-sales.png" label="Sales" />
          </Piece>
          <Piece at={{ l: 270, t: 100, depth: 1.3 }}>
            <Photo file="photo-doorstep.jpg" label="Doorstep" tilt={-8} alt="A parcel and a bag of groceries on a doorstep" />
          </Piece>
          <Piece at={{ l: 214, t: 118, depth: 1.1 }}>
            <Note className="max-w-[11rem]">from our hands to theirs, arriving whole</Note>
          </Piece>
          <Piece at={{ l: 300, t: 56 }}>
            <Arrow flip />
          </Piece>

          {/* 3: settle up, enters from above */}
          <Piece at={{ l: 352, t: -18 }}>
            <div data-word-main className="flex items-start gap-3">
              <Count n={3} />
              <CharText as="p" text="To settle up" className="giant-word giant-word-long font-display uppercase text-forest-ink" />
            </div>
          </Piece>
          <Piece at={{ l: 345, t: 30, depth: 1.2 }}>
            <Photo file="photo-ledger.jpg" label="Ledger" tilt={5} alt="A hand writing in a khata ledger" />
          </Piece>
          <Piece at={{ l: 440, t: 22, depth: 0.8 }}>
            <Disc file="disc-khata.png" label="Khata" />
          </Piece>
          <Piece at={{ l: 470, t: -10, depth: 1.25 }}>
            <Photo file="photo-handover.jpg" label="Handover" tilt={8} alt="Two hands handing over a wrapped parcel at a gate" />
          </Piece>
          <Piece at={{ l: 396, t: -2, depth: 1.1 }}>
            <Note className="max-w-[10rem]">every rupee, written down</Note>
          </Piece>
        </div>
      </div>
    </section>
  );
}
