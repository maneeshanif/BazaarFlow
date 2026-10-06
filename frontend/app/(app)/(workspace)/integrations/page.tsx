"use client";

import { RequireRole } from "@/components/app/RequireRole";
import { IntegrationsView } from "@/components/integrations/IntegrationsView";

/** Integrations (PRD F-018). Owners only. */
export default function IntegrationsPage() {
  return (
    <RequireRole roles={["owner"]}>
      <IntegrationsView />
    </RequireRole>
  );
}
