"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { TONE_CLASS, type Tone } from "@/components/brand/tones";

type Props = {
  /** file name inside public/brand, e.g. "hero-roll.png" (see docs/design/asset-prompts.md) */
  file: string;
  alt: string;
  /** shown on the placeholder until the real file exists */
  label?: string;
  tone?: Tone;
  className?: string;
  /** the image is decoration: hide it from assistive technology */
  decorative?: boolean;
};

/**
 * An image from public/brand. The owner supplies the artwork later (ADR 0005); until a file exists, or if it fails to
 * load, a coloured placeholder of the same box is drawn so layouts are never broken or empty.
 */
export function BrandImage({ file, alt, label, tone = "lime", className, decorative = false }: Props) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <div
        role={decorative ? undefined : "img"}
        aria-label={decorative ? undefined : alt}
        aria-hidden={decorative || undefined}
        data-placeholder={file}
        className={cn("flex h-full w-full items-center justify-center p-3 text-center font-display text-ui-lg uppercase leading-none", TONE_CLASS[tone], className)}
      >
        {label ?? file}
      </div>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element -- local brand art with a placeholder fallback; next/image would hide onError
    <img
      src={`/brand/${file}`}
      alt={decorative ? "" : alt}
      aria-hidden={decorative || undefined}
      onError={() => setFailed(true)}
      // an image that failed before React hydrated never fires onError: check it as soon as it is attached
      ref={(el) => {
        if (el && el.complete && el.naturalWidth === 0) setFailed(true);
      }}
      loading="lazy"
      decoding="async"
      className={cn("h-full w-full object-cover", className)}
    />
  );
}
