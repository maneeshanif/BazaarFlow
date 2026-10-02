import type { ReactNode } from "react";
import { RequireRole } from "@/components/app/RequireRole";
import { AuthProvider } from "@/lib/auth/AuthProvider";

/** Everything under /dashboard needs a signed-in member of the shop (any role). */
export default function DashboardGuardLayout({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <RequireRole roles={["owner", "manager", "staff"]}>{children}</RequireRole>
    </AuthProvider>
  );
}
