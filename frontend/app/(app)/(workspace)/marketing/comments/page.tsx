"use client";

import { RequireRole } from "@/components/app/RequireRole";
import { CommentsView } from "@/components/marketing/CommentsView";

/** Facebook comments and the replies proposed for them (PRD W-004). Owners and managers. */
export default function CommentsPage() {
  return (
    <RequireRole roles={["owner", "manager"]}>
      <CommentsView />
    </RequireRole>
  );
}
