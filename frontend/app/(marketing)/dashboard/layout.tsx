import type { ReactNode } from "react";
import { RequireRole } from "@/components/app/RequireRole";

/** Everything under /dashboard needs a signed-in member of the shop (any role). */
export default function DashboardGuardLayout({ children }: { children: ReactNode }) {
  return <RequireRole roles={["owner", "manager", "staff"]}>{children}</RequireRole>;
}
