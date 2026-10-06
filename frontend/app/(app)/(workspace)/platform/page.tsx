"use client";

import { PlatformOverviewView } from "@/components/platform/PlatformOverviewView";
import { RequireOperator } from "@/components/platform/RequireOperator";

/** The platform overview (PRD D-004). BazaarFlow operators only. */
export default function PlatformPage() {
  return (
    <RequireOperator>
      <PlatformOverviewView />
    </RequireOperator>
  );
}
