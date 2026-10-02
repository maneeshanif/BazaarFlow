import type { ReactNode } from "react";
import { RequireRole } from "@/components/app/RequireRole";

/** Marketing is for owners and managers (PRD section 14.2). A template wraps the existing layout without editing it. */
export default function MarketingGuardTemplate({ children }: { children: ReactNode }) {
  return <RequireRole roles={["owner", "manager"]}>{children}</RequireRole>;
}
