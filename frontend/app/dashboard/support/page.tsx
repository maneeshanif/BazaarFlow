"use client";

import SupportVoicePage from "@/app/support/voice/page";
import { DashboardLayout } from "@/components/DashboardSidebar";

export default function CustomerSupportPage() {
  return (
    <DashboardLayout>
      <SupportVoicePage />
    </DashboardLayout>
  );
}
