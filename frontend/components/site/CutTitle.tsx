"use client";

import { useRef, type CSSProperties } from "react";
import { PROXIMITY_HEADING, useProximity } from "@/components/site/text";

/** Fixed, hand-picked turns and drops, so each letter looks cut from paper and the page never differs between renders. */
const TURN = [-4, 3, -2, 4, -3, 2, -5, 3, -2, 4, -1, 2];
const DROP = [0, 2, -2, 3, -1, 2, -3, 1, 3, -2, 2, -1];

/** One word of hand-cut letters. `from` offsets the pattern and the entrance delay so lines do not repeat each other. */
export function CutWord({ text, from = 0 }: { text: string; from?: number }) {
  let n = from;
  return (
    <span className="inline-block whitespace-nowrap">
      {Array.from(text).map((ch, i) => {
        const k = n++;
        const style = { "--r": `${TURN[k % TURN.length]}deg`, "--r0": `${TURN[(k + 5) % TURN.length] * 3}deg`, "--dy": `${DROP[k % DROP.length]}%`, "--delay": `${0.05 * k}s` } as CSSProperties;
        return (
          <span key={i} data-cut className="cut-letter" style={style}>
            <span data-prox className="inline-block">
              {ch === " " ? " " : ch}
            </span>
          </span>
        );
      })}
    </span>
  );
}

/**
 * A page title of very large hand-cut capitals, one line per entry. The letters drop in after the opening (when there is
 * one) and lean away from the pointer as it passes. The whole title is exposed once to assistive technology.
 */
export function CutTitle({ lines, className }: { lines: string[]; className?: string }) {
  const ref = useRef<HTMLHeadingElement | null>(null);
  useProximity(ref, { ...PROXIMITY_HEADING, radius: 2.1, lift: 0.06 });
  // where each line starts in the letter pattern, so no two lines repeat each other
  const starts = lines.map((_, i) => lines.slice(0, i).reduce((sum, l) => sum + l.length, 0));
  return (
    <h1 ref={ref} className={className}>
      <span className="sr-only">{lines.join(" ")}</span>
      <span aria-hidden className="block">
        {lines.map((line, i) => (
          <span key={line} className="hero-giant block">
            <CutWord text={line} from={starts[i]} />
          </span>
        ))}
      </span>
    </h1>
  );
}
