"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { RequireRole } from "@/components/app/RequireRole";
import { ErrorState, UnauthorizedState } from "@/components/app/StateViews";
import { CustomerForm } from "@/components/customers/CustomerForm";
import { LedgerPanel } from "@/components/customers/LedgerPanel";
import { Skeleton } from "@/components/ui/skeleton";
import { useLoad } from "@/hooks/useLoad";
import { apiGet } from "@/lib/api/client";
import type { Customer } from "@/lib/api/types";

function CustomerPage() {
  const { id } = useParams<{ id: string }>();
  const [override, setOverride] = useState<Customer | null>(null);
  const loaded = useLoad(() => apiGet<Customer>(`/customers/${id}`), [id]);

  if (loaded.state === "loading") {
    return (
      <div role="status" aria-busy="true" aria-label="Loading customer" className="flex max-w-form flex-col gap-3">
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
        message={notFound ? "That customer does not exist or was deleted." : (loaded.error?.message ?? "Could not load this customer.")}
        onRetry={notFound ? undefined : loaded.reload}
      />
    );
  }

  const customer = override ?? loaded.data;
  return (
    <div className="flex flex-col gap-8">
      <CustomerForm key={customer.updated_at} customer={customer} onSaved={(c) => setOverride({ ...c, balance: customer.balance })} />
      <LedgerPanel customer={customer} onChanged={(balance) => setOverride({ ...customer, balance })} />
    </div>
  );
}

/** One customer: details (managers edit) and the udhaar ledger. Owners and managers only. */
export default function CustomerDetailPage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <CustomerPage />
    </RequireRole>
  );
}
