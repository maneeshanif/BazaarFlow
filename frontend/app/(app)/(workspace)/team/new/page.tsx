"use client";

import { RequireRole } from "@/components/app/RequireRole";
import { TeamMemberForm } from "@/components/team/TeamMemberForm";

/** Add a team member (PRD F-019). Owner only. */
export default function NewTeamMemberPage() {
  return (
    <RequireRole roles={["owner"]}>
      <TeamMemberForm />
    </RequireRole>
  );
}
