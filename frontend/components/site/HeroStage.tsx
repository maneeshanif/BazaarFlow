"use client";

import dynamic from "next/dynamic";
import { BrandImage } from "@/components/brand/BrandImage";
import { BrandVideo } from "@/components/site/BrandVideo";

/** Three.js is loaded only in the browser and only for the hero; everyone else gets the picture. */
const HeroParcels3D = dynamic(() => import("@/components/site/HeroParcels3D"), { ssr: false });

/**
 * The hero object. If the owner has supplied `hero-parcels.mp4` (docs/design/asset-prompts.md) that loops here; otherwise the
 * Three.js parcels are built in the browser; otherwise, with no WebGL or with reduced motion, the picture.
 */
export function HeroStage() {
  const picture = (
    <div className="mx-auto h-full max-w-xl">
      <BrandImage file="hero-parcels.png" alt="A stack of small delivery parcels and a tiffin carrier" label="Parcels" tone="forest" className="object-contain" />
    </div>
  );
  return (
    <div className="relative h-[17rem] w-full sm:h-[22rem] lg:h-[28rem]" data-testid="hero-stage">
      <BrandVideo name="hero-parcels" label="A stack of small delivery parcels and a tiffin carrier" fallback={<HeroParcels3D fallback={picture} />} />
    </div>
  );
}
