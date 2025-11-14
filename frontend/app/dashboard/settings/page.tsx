"use client";

import SalesSettingsForm from "@/components/sales/SalesSettingsForm";
import { SalesVendorProvider } from "@/components/sales/VendorContext";
import { DashboardLayout } from "@/components/DashboardSidebar";

export default function DashboardSettingsPage() {
  return (
    <DashboardLayout>
      <SalesVendorProvider>
        <div className="space-y-6">
          <div className="space-y-2">
            <h1 className="text-3xl font-semibold text-[#174143]">WhatsApp Business Settings</h1>
            <p className="text-sm text-slate-600">
              Connect your Meta Business credentials once here. These credentials power every sales workflow across the dashboard.
            </p>
          </div>
          <SalesSettingsForm />
        </div>
      </SalesVendorProvider>
    </DashboardLayout>
  );
}
