"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { AppShell } from "@/components/app/AppShell";
import { useLoad } from "@/hooks/useLoad";
import { useAuth } from "@/lib/auth/AuthProvider";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { activeHrefFor } from "@/lib/navigation";

type Me = components["schemas"]["MeOut"];

/**
 * The signed-in frame for every workspace page: the AppShell with the shop and user name taken from /auth/me.
 * Mounted inside RequireRole, so a role is always present here.
 */
export function WorkspaceShell({ children }: { children: ReactNode }) {
  const { role, tenantId } = useAuth();
  const pathname = usePathname();
  const me = useLoad(() => apiGet<Me>("/auth/me"), [tenantId]);

  const shop = me.data?.memberships.find((m) => m.tenant_id === me.data?.tenant_id)?.tenant_name;
  return (
    <AppShell
      role={role ?? "staff"}
      platformAdmin={me.data?.user.is_platform_admin ?? false}
      tenantName={shop ?? "Your shop"}
      userName={me.data?.user.name ?? undefined}
      activeHref={activeHrefFor(pathname)}
    >
      {children}
    </AppShell>
  );
}
