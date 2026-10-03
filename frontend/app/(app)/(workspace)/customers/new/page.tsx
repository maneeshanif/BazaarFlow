"use client";

import { RequireRole } from "@/components/app/RequireRole";
import { CustomerForm } from "@/components/customers/CustomerForm";

/** Add a customer (PRD F-009). Owners and managers only. */
export default function NewCustomerPage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <CustomerForm />
    </RequireRole>
  );
}
