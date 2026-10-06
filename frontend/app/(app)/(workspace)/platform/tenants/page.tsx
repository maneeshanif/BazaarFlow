"use client";

import { RequireOperator } from "@/components/platform/RequireOperator";
import { TenantsView } from "@/components/platform/TenantsView";

/** Platform admin: shops (PRD F-025). BazaarFlow operators only. */
export default function PlatformTenantsPage() {
  return (
    <RequireOperator>
      <TenantsView />
    </RequireOperator>
  );
}
