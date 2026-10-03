"use client";

import { SaleForm } from "@/components/sales/SaleForm";

/** New sale (PRD F-007). Every role can record a sale; the API decides what each may do. */
export default function NewSalePage() {
  return <SaleForm />;
}
