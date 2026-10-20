"use client";

import dynamic from "next/dynamic";
import { BrandImage } from "@/components/brand/BrandImage";

/** Three.js is loaded only in the browser and only for the hero; everyone else gets the picture. */
const HeroRoll3D = dynamic(() => import("@/components/site/HeroRoll3D"), { ssr: false });

export function HeroStage() {
  return (
    <div className="relative h-[22rem] w-full sm:h-[28rem] lg:h-[36rem]" data-testid="hero-stage">
      <HeroRoll3D
        fallback={
          <div className="mx-auto h-full max-w-md overflow-hidden rounded-full">
            <BrandImage file="hero-roll.png" alt="A roll of BazaarFlow tape" label="Hero roll" tone="forest" />
          </div>
        }
      />
    </div>
  );
}
