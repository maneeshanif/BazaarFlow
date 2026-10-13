"use client";

import { RequireRole } from "@/components/app/RequireRole";
import { PurchaseOrdersView } from "@/components/purchasing/PurchaseOrdersView";

/** Draft purchase orders (PRD W-006). Owners and managers. */
export default function PurchaseOrdersPage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <PurchaseOrdersView />
    </RequireRole>
  );
}
