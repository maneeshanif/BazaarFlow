"use client";

import { RequireRole } from "@/components/app/RequireRole";
import { OnboardingWizard } from "@/components/onboarding/OnboardingWizard";

/** The onboarding wizard (PRD F-003). Owners only. */
export default function OnboardingPage() {
  return (
    <RequireRole roles={["owner"]}>
      <OnboardingWizard />
    </RequireRole>
  );
}
