"use client";

import { RequireRole } from "@/components/app/RequireRole";
import { FinanceView } from "@/components/finance/FinanceView";

/** The owner's finance dashboard (PRD D-002): revenue trend, gross margin, receivables, vendor payables, cash vs credit. */
export default function FinanceDashboardPage() {
  return (
    <RequireRole roles={["owner"]}>
      <FinanceView endpoint="/finance/dashboard" title="Finance dashboard" description="The five numbers that tell you how the money is doing." />
    </RequireRole>
  );
}
