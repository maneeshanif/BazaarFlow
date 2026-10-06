"use client";

import { RequireRole } from "@/components/app/RequireRole";
import { FinanceView } from "@/components/finance/FinanceView";

/** Finance overview and cash book (PRD F-013). Owners see everything, managers a reduced view. */
export default function FinancePage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <FinanceView endpoint="/finance/overview" title="Finance" description="Revenue, who owes you, and where the money moved." showCashBook />
    </RequireRole>
  );
}
