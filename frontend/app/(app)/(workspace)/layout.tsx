import type { ReactNode } from "react";
import { RequireRole } from "@/components/app/RequireRole";
import { WorkspaceShell } from "@/components/app/WorkspaceShell";

/** Every workspace page needs a signed-in member of the shop (any role); pages narrow it further themselves. */
export default function WorkspaceLayout({ children }: { children: ReactNode }) {
  return (
    <RequireRole roles={["owner", "manager", "staff"]}>
      <WorkspaceShell>{children}</WorkspaceShell>
    </RequireRole>
  );
}
