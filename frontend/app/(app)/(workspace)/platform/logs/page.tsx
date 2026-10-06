"use client";

import { LogsView } from "@/components/platform/LogsView";
import { RequireOperator } from "@/components/platform/RequireOperator";

/** System logs (PRD F-028). BazaarFlow operators only. */
export default function PlatformLogsPage() {
  return (
    <RequireOperator>
      <LogsView />
    </RequireOperator>
  );
}
