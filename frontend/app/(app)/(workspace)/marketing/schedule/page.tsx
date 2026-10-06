"use client";

import { RequireRole } from "@/components/app/RequireRole";
import { ScheduleView } from "@/components/marketing/ScheduleView";

/** The posting schedule (PRD F-015). Owners and managers. */
export default function SchedulePage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <ScheduleView />
    </RequireRole>
  );
}
