"use client";

import { RequireRole } from "@/components/app/RequireRole";
import { ActivityView } from "@/components/marketing/ActivityView";

/** Marketing activity (PRD F-016). Owners and managers. */
export default function ActivityPage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <ActivityView />
    </RequireRole>
  );
}
