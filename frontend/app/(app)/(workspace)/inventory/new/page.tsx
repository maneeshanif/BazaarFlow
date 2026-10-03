"use client";

import { RequireRole } from "@/components/app/RequireRole";
import { ProductForm } from "@/components/inventory/ProductForm";

/** Add a product (PRD F-010). Owners and managers only; staff see "Access is restricted". */
export default function NewProductPage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <ProductForm />
    </RequireRole>
  );
}
