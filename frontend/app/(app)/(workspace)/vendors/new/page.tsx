"use client";

import { RequireRole } from "@/components/app/RequireRole";
import { VendorForm } from "@/components/vendors/VendorForm";

/** Add a vendor (PRD F-012). Owners and managers only. */
export default function NewVendorPage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <VendorForm />
    </RequireRole>
  );
}
