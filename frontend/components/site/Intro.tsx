"use client";

import { useEffect, useSyncExternalStore } from "react";
import { BrandImage } from "@/components/brand/BrandImage";

const KEY = "bazaarflow-intro-seen";

function seen(): boolean {
  try {
    return window.sessionStorage.getItem(KEY) === "1";
  } catch {
    return true; // storage blocked: skip the intro rather than repeat it
  }
}

/**
 * The first-visit moment: a lime screen with the logo badge that lifts away. Shown once per browser session, never
 * for reduced motion, never blocks input (it fades itself out with CSS and ignores the pointer).
 */
export function Intro() {
  const show = useSyncExternalStore(
    () => () => {},
    () => !seen() && !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    () => false,
  );
  useEffect(() => {
    if (!show) return;
    try {
      window.sessionStorage.setItem(KEY, "1");
    } catch {
      /* ignore */
    }
  }, [show]);
  if (!show) return null;
  return (
    <div
      aria-hidden
      data-testid="intro"
      className="pointer-events-none fixed inset-0 z-[70] flex items-center justify-center bg-lime"
      style={{ animation: "arc-leave 0.7s 1.3s cubic-bezier(0.7,0,0.3,1) forwards" }}
    >
      <div className="h-28 w-44 overflow-hidden rounded-card">
        <BrandImage file="logo-badge.png" alt="" decorative label="BazaarFlow" tone="forest" />
      </div>
    </div>
  );
}
