"use client";

import { RequireRole } from "@/components/app/RequireRole";
import { InboxView } from "@/components/inbox/InboxView";

/** The unified inbox (PRD F-005). Every role in the shop. */
export default function InboxPage() {
  return (
    <RequireRole roles={["owner", "manager", "staff"]}>
      <InboxView />
    </RequireRole>
  );
}
