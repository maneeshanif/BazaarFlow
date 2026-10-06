"use client";

import { RequireRole } from "@/components/app/RequireRole";
import { InsightsView } from "@/components/marketing/InsightsView";

/** Marketing insights (PRD F-017). Owners and managers. */
export default function InsightsPage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <InsightsView />
    </RequireRole>
  );
}
