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
  const [kind, setKind] = useState<"webm" | "mp4">("mp4");
  const video = useRef<HTMLVideoElement | null>(null);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      queueMicrotask(() => setState("no"));
      return;
    }
    let live = true;
    // a .webm (VP9 with transparency, for the hero) wins where the browser can play it; otherwise the .mp4
    const probe = (ext: "webm" | "mp4") =>
      fetch(`/brand/${name}.${ext}`, { method: "HEAD" }).then((r) => r.ok && (r.headers.get("content-type") ?? "").startsWith("video"));
    const canWebm = document.createElement("video").canPlayType('video/webm; codecs="vp9"') !== "";
    (canWebm ? probe("webm") : Promise.resolve(false))
      .catch(() => false)
      .then((w) => (w ? "webm" : probe("mp4").then((m) => (m ? "mp4" : null))))
      .then((k) => {
        if (!live) return;
        if (k) setKind(k);
        setState(k ? "yes" : "no");
      })
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
      <source src={`/brand/${name}.${kind}`} type={`video/${kind}`} />
    </video>
  );
}
