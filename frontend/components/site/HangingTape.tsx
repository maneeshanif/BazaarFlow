"use client";

import dynamic from "next/dynamic";

const HangingTape3D = dynamic(() => import("@/components/site/HangingTape3D"), { ssr: false });

/** The loose roll of tape above the board; see HangingTape3D. */
export function HangingTape() {
  return <HangingTape3D />;
}
