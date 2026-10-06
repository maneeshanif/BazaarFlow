"use client";

import { AgentDashboardView } from "@/components/agent/AgentDashboardView";
import { RequireRole } from "@/components/app/RequireRole";

/** The agent command center (PRD D-003). Owners and managers only. */
export default function AgentsPage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <AgentDashboardView />
    </RequireRole>
  );
}
