"use client";

import type { ReactNode } from "react";
import { RequireRole } from "@/components/app/RequireRole";
import { UnauthorizedState } from "@/components/app/StateViews";
import { Skeleton } from "@/components/ui/skeleton";
import { useLoad } from "@/hooks/useLoad";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { useAuth } from "@/lib/auth/AuthProvider";

type Me = components["schemas"]["MeOut"];

function OperatorGate({ children }: { children: ReactNode }) {
  const { tenantId } = useAuth();
  const me = useLoad(() => apiGet<Me>("/auth/me"), [tenantId]);
  if (me.state === "loading") return <Skeleton className="h-32 w-full" />;
  if (!me.data?.user.is_platform_admin) return <UnauthorizedState />;
  return <>{children}</>;
}

/** Platform pages are for BazaarFlow operators only (the API enforces the same with require_platform_admin). */
export function RequireOperator({ children }: { children: ReactNode }) {
  return (
    <RequireRole roles={["owner", "manager", "staff"]}>
      <OperatorGate>{children}</OperatorGate>
    </RequireRole>
  );
}
