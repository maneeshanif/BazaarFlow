"use client";

import dynamic from "next/dynamic";
import { BrandImage } from "@/components/brand/BrandImage";

/** Three.js is loaded only in the browser and only for the hero; everyone else gets the picture. */
const HeroParcels3D = dynamic(() => import("@/components/site/HeroParcels3D"), { ssr: false });

export function HeroStage() {
  return (
    <div className="relative h-[17rem] w-full sm:h-[22rem] lg:h-[28rem]" data-testid="hero-stage">
      <HeroParcels3D
        fallback={
          <div className="mx-auto h-full max-w-xl">
            <BrandImage file="hero-parcels.png" alt="A stack of small delivery parcels and a tiffin carrier" label="Parcels" tone="forest" className="object-contain" />
          </div>
        }
      />
    </div>
  );
}
