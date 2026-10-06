"use client";

import { RequireRole } from "@/components/app/RequireRole";
import { VoiceView } from "@/components/voice/VoiceView";

/** Voice calls and agent settings (PRD F-023). Owners edit; managers can read. */
export default function VoicePage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <VoiceView />
    </RequireRole>
  );
}
