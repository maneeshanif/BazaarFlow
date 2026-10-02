import type { ReactNode } from "react";
import { RequireRole } from "@/components/app/RequireRole";

/** Shop settings are owner-only (PRD section 14.2). */
export default function SettingsGuardLayout({ children }: { children: ReactNode }) {
  return <RequireRole roles={["owner"]}>{children}</RequireRole>;
}
