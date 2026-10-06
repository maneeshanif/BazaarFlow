"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { RequireRole } from "@/components/app/RequireRole";
import { ErrorState, UnauthorizedState } from "@/components/app/StateViews";
import { PayablesPanel } from "@/components/vendors/PayablesPanel";
import { VendorForm } from "@/components/vendors/VendorForm";
import { Skeleton } from "@/components/ui/skeleton";
import { useLoad } from "@/hooks/useLoad";
import { apiGet } from "@/lib/api/client";
import type { ShopVendor } from "@/lib/api/types";

function VendorPage() {
  const { id } = useParams<{ id: string }>();
  const [override, setOverride] = useState<ShopVendor | null>(null);
  const loaded = useLoad(() => apiGet<ShopVendor>(`/vendors/${id}`), [id]);

  if (loaded.state === "loading") {
    return (
      <div role="status" aria-busy="true" aria-label="Loading vendor" className="flex max-w-form flex-col gap-3">
        <Skeleton className="h-6 w-56" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }
  if (loaded.state === "unauthorized") return <UnauthorizedState />;
  if (loaded.state === "error" || !loaded.data) {
    const notFound = loaded.error?.status === 404;
    return (
      <ErrorState
        message={notFound ? "That vendor does not exist or was deleted." : (loaded.error?.message ?? "Could not load this vendor.")}
        onRetry={notFound ? undefined : loaded.reload}
      />
    );
  }

  const vendor = override ?? loaded.data;
  return (
    <div className="flex flex-col gap-8">
      <VendorForm key={vendor.updated_at} vendor={vendor} onSaved={(v) => setOverride({ ...v, balance: vendor.balance })} />
      <PayablesPanel vendor={vendor} onChanged={(balance) => setOverride({ ...vendor, balance })} />
    </div>
  );
}

/** One vendor: details and what you owe them. Owners and managers only. */
export default function VendorDetailPage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <VendorPage />
    </RequireRole>
  );
}
