"use client";

import { AutomationsView } from "@/components/automations/AutomationsView";
import { RequireRole } from "@/components/app/RequireRole";

/** Automation recipes (PRD F-024). Owners and managers. */
export default function AutomationsPage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <AutomationsView />
    </RequireRole>
  );
}
