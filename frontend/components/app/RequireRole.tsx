"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { UnauthorizedState } from "@/components/app/StateViews";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth/AuthProvider";
import type { Role } from "@/lib/navigation";

/**
 * Route guard. Visitors who are not signed in go to /sign-in (and come back afterwards); a signed-in user whose
 * role is not allowed sees the "Access is restricted" view instead of the page. This is a convenience: the API
 * rejects the same requests with 401/403 whatever the UI does.
 */
export function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const { status, role } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "anonymous") {
      // read at redirect time (not via useSearchParams, which forces a Suspense boundary on every guarded page)
      const query = window.location.search.replace(/^\?/, "");
      router.replace(`/sign-in?next=${encodeURIComponent(query ? `${pathname}?${query}` : pathname)}`);
    }
  }, [status, router, pathname]);

  if (status === "loading") {
    return (
      <div role="status" aria-busy="true" aria-label="Loading" className="flex flex-col gap-3 p-6">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }
  if (status === "anonymous") return null;
  if (!role || !roles.includes(role)) return <UnauthorizedState />;
  return <>{children}</>;
}
