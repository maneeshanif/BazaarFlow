"use client";

import { useState } from "react";
import { RequireRole } from "@/components/app/RequireRole";
import { ErrorState, UnauthorizedState } from "@/components/app/StateViews";
import { ShopSettingsForm } from "@/components/settings/ShopSettingsForm";
import { Skeleton } from "@/components/ui/skeleton";
import { useLoad } from "@/hooks/useLoad";
import { apiGet } from "@/lib/api/client";
import type { ShopSettings } from "@/lib/api/types";

function SettingsPage() {
  const [override, setOverride] = useState<ShopSettings | null>(null);
  const loaded = useLoad(() => apiGet<ShopSettings>("/settings/shop"), []);

  if (loaded.state === "loading") {
    return (
      <div role="status" aria-busy="true" aria-label="Loading shop profile" className="flex max-w-form flex-col gap-3">
        <Skeleton className="h-6 w-56" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }
  if (loaded.state === "unauthorized") return <UnauthorizedState />;
  if (loaded.state === "error" || !loaded.data) {
    return <ErrorState message={loaded.error?.message ?? "Could not load your shop profile."} onRetry={loaded.reload} />;
  }
  const shop = override ?? loaded.data;
  return <ShopSettingsForm key={shop.updated_at} shop={shop} onSaved={setOverride} />;
}

/** The shop profile and settings (PRD F-020). Owners only. */
export default function ShopSettingsPage() {
  return (
    <RequireRole roles={["owner"]}>
      <SettingsPage />
    </RequireRole>
  );
}
