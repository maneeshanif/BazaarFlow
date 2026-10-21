"use client";

import { RequireRole } from "@/components/app/RequireRole";
import { SupportCall } from "@/components/voice/SupportCall";

/** Voice test calls with the support assistant. Owners and managers only. */
export default function SupportCallsPage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <SupportCall />
    </RequireRole>
  );
}
