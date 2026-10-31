"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const LAYERS = ["bg-lime", "bg-coral", "bg-orange", "bg-sunny", "bg-sky", "bg-indigo"];
const SECONDS = 1.7;

/**
 * The reference reuses its opening's curved sheets whenever you move to another page. The new page is already underneath;
 * the coloured sheets cover it for an instant and lift away one after the other, so every page is "uncovered" the same way
 * the first one is. Not shown on the first page of a load (the opening does that) and never for reduced motion (CSS).
 */
export function PageCurtain() {
  const pathname = usePathname();
  const [seen, setSeen] = useState(pathname);
  const [run, setRun] = useState(0);
  const [done, setDone] = useState(0);
  if (pathname !== seen) {
    setSeen(pathname);
    setRun((r) => r + 1);
  }
  useEffect(() => {
    if (!run) return;
    const t = window.setTimeout(() => setDone(run), SECONDS * 1000);
    return () => window.clearTimeout(t);
  }, [run]);
  if (!run || done === run) return null;
  return (
    <div key={run} aria-hidden data-testid="page-curtain" className="page-curtain fixed inset-0 z-[140]">
      {LAYERS.map((tone, i) => (
        <div
          key={i}
          className={`absolute inset-0 ${tone} rounded-b-[50%_14vh]`}
          style={{ zIndex: LAYERS.length - i, animation: `arc-leave 0.85s ${0.12 + i * 0.07}s cubic-bezier(0.7,0,0.3,1) both` }}
        />
      ))}
    </div>
  );
}
