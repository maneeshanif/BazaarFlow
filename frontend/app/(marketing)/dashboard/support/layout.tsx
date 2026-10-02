import type { ReactNode } from "react";
import { RequireRole } from "@/components/app/RequireRole";

/** The support / voice area is for owners and managers. */
export default function SupportGuardLayout({ children }: { children: ReactNode }) {
  return <RequireRole roles={["owner", "manager"]}>{children}</RequireRole>;
}
