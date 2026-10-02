import type { ReactNode } from "react";
import { RequireRole } from "@/components/app/RequireRole";

/** Integration credentials are owner-only (navigation.ts: "Integrations"; PRD section 14.2). */
export default function CredentialsGuardLayout({ children }: { children: ReactNode }) {
  return <RequireRole roles={["owner"]}>{children}</RequireRole>;
}
