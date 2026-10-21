"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import axios from "axios";
import { MessageCircle, Settings2, Users, History, Send, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { DashboardLayout } from "@/components/DashboardSidebar";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { SalesVendorProvider, useSalesVendor } from "@/components/sales/VendorContext";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

interface VendorSummary {
  vendor_id: string;
  phone_number_id: string;
  name?: string;
  waba_id?: string;
}

const navItems = [
  { label: "My Users", href: "/dashboard/sales/my-users", icon: Users },
  { label: "History", href: "/dashboard/sales/history", icon: History },
  { label: "Ask Sales Agent", href: "/dashboard/sales/ask", icon: MessageCircle },
  { label: "Settings", href: "/dashboard/sales/settings", icon: Settings2 },
];

function SalesShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { vendorId, setVendorId } = useSalesVendor();
  const [draft, setDraft] = useState(vendorId);
  const [vendors, setVendors] = useState<VendorSummary[]>([]);
  const [loadingVendors, setLoadingVendors] = useState(false);
  const [vendorError, setVendorError] = useState<string | null>(null);

  const fetchVendors = useCallback(async () => {
    try {
      setLoadingVendors(true);
      setVendorError(null);
      const { data } = await axios.get<VendorSummary[]>(`${API_BASE}/api/vendors`);
      setVendors(data);
    } catch (err) {
      setVendorError("Unable to load vendor list.");
      if (axios.isAxiosError(err)) {
        toast.error("Vendor list fetch failed", {
          description: err.response?.data?.detail ?? err.message,
        });
      }
    } finally {
      setLoadingVendors(false);
    }
  }, []);

  useEffect(() => {
    fetchVendors();
  }, [fetchVendors]);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    setVendorId(draft.trim());
  };

  const handleSelectVendor = (value: string) => {
    setVendorId(value);
    setDraft(value);
  };

  const selectedVendor = useMemo(() => vendors.find((item) => item.vendor_id === vendorId), [vendors, vendorId]);

  useEffect(() => {
    setDraft(vendorId);
  }, [vendorId]);

  return (
    <div className="space-y-6">
      <Card className="p-6 bg-gradient-to-r from-[#174143] to-[#427A76] text-white">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm text-white/80">WhatsApp Sales Workspace</p>
            <h1 className="text-3xl font-semibold">Sales Control Center</h1>
            <p className="text-sm text-white/70 mt-1">
              Manage vendor credentials, monitor conversations, and interact with the AI sales agent.
            </p>
          </div>
          <div className="flex flex-col gap-3 md:items-end">
            <div className="flex flex-col gap-2 md:flex-row md:items-center">
              <Select
                value={selectedVendor ? selectedVendor.vendor_id : undefined}
                onValueChange={handleSelectVendor}
                disabled={loadingVendors || vendors.length === 0}
              >
                <SelectTrigger className="w-full bg-white/20 border-white/40 text-white placeholder:text-white/60 md:w-64">
                  <SelectValue placeholder={loadingVendors ? "Loading vendors..." : "Select vendor"} />
                </SelectTrigger>
                <SelectContent>
                  {vendors.map((vendor) => (
                    <SelectItem key={vendor.vendor_id} value={vendor.vendor_id}>
                      <span className="font-medium">{vendor.name || vendor.phone_number_id}</span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                type="button"
                variant="secondary"
                className="bg-white text-[#174143] hover:bg-white/90"
                onClick={fetchVendors}
                disabled={loadingVendors}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Refresh
              </Button>
            </div>
            <form onSubmit={handleSubmit} className="flex flex-col gap-2 md:flex-row md:items-center">
              <Input
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Vendor ID"
                className="bg-white/20 border-white/40 text-white placeholder:text-white/60"
              />
              <Button type="submit" variant="secondary" className="bg-white text-[#174143] hover:bg-white/90">
                Update Vendor
              </Button>
            </form>
            {vendorError && <p className="text-xs text-red-100">{vendorError}</p>}
            {selectedVendor && (
              <p className="text-xs text-white/80">
                Active vendor: <span className="font-semibold">{selectedVendor.name || selectedVendor.vendor_id}</span>
              </p>
            )}
          </div>
        </div>
      </Card>

      <nav className="flex flex-wrap gap-3">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link key={item.href} href={item.href} className="no-underline">
              <Button
                variant={active ? "default" : "outline"}
                className={active ? "bg-[#174143] hover:bg-[#174143]/90 text-white" : ""}
              >
                <Icon className="w-4 h-4 mr-2" />
                {item.label}
              </Button>
            </Link>
          );
        })}
      </nav>

      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm">
        {vendorId ? (
          children
        ) : (
          <div className="flex flex-col items-center justify-center gap-3 py-12 text-center text-slate-500">
            <Send className="w-12 h-12 text-[#174143]/70" />
            <p className="text-lg font-medium">Enter a vendor ID to get started.</p>
            <p className="text-sm max-w-md">
              Create a vendor via the settings form or use an existing ID from the webhook database. The selection is saved locally.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}

export default function DashboardSalesLayout({ children }: { children: React.ReactNode }) {
  return (
    <DashboardLayout>
      <SalesVendorProvider>
        <SalesShell>{children}</SalesShell>
      </SalesVendorProvider>
    </DashboardLayout>
  );
}
