"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * A looping, silent clip from `public/brand/<name>.mp4` (and `.webm`, if you supply both), for the places the owner wants
 * moving pictures instead of stills (docs/design/asset-prompts.md, "Video"). Until the file exists, or for people who ask
 * for reduced motion, `fallback` is drawn instead, so the page is never empty and never waits on a missing file.
 */
export function BrandVideo({ name, fallback, className, label }: { name: string; fallback: ReactNode; className?: string; label?: string }) {
  const [state, setState] = useState<"checking" | "yes" | "no">("checking");
  const video = useRef<HTMLVideoElement | null>(null);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      queueMicrotask(() => setState("no"));
      return;
    }
    let live = true;
    fetch(`/brand/${name}.mp4`, { method: "HEAD" })
      .then((r) => live && setState(r.ok && (r.headers.get("content-type") ?? "").startsWith("video") ? "yes" : "no"))
      .catch(() => live && setState("no"));
    return () => {
      live = false;
    };
  }, [name]);
  if (state !== "yes") return <>{fallback}</>;
  return (
    <video
      ref={video}
      className={cn("h-full w-full object-contain", className)}
      autoPlay
      muted
      loop
      playsInline
      preload="metadata"
      aria-label={label}
      aria-hidden={label ? undefined : true}
      onError={() => setState("no")}
    >
      <source src={`/brand/${name}.webm`} type="video/webm" />
      <source src={`/brand/${name}.mp4`} type="video/mp4" />
    </video>
  );
}
