"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, CalendarClock, BarChart3, ShieldCheck, Megaphone } from "lucide-react";

import { DashboardLayout } from "@/components/DashboardSidebar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

import { MarketingProvider } from "./MarketingContext";

const navItems = [
  { label: "Overview", href: "/dashboard/marketing/overview", icon: LayoutDashboard },
  { label: "Schedule", href: "/dashboard/marketing/schedule", icon: CalendarClock },
  { label: "Activity", href: "/dashboard/marketing/activity", icon: BarChart3 },
  { label: "Credentials", href: "/dashboard/marketing/credentials", icon: ShieldCheck },
];

function MarketingShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="space-y-6">
      <Card className="p-6 text-white bg-gradient-to-r from-[#174143] to-[#427A76]">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div className="space-y-3">
            <Badge className="w-fit bg-white/20 text-white border-white/30">
              <Megaphone className="mr-2 h-3.5 w-3.5" /> Marketing Agent
            </Badge>
            <div>
              <h1 className="text-3xl font-semibold">Marketing Automation Command Center</h1>
              <p className="mt-1 text-sm text-white/80 max-w-2xl">
                Connect your Facebook presence, orchestrate AI-generated campaigns, and monitor performance without leaving BazaarFlow.
              </p>
            </div>
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
                <Icon className="mr-2 h-4 w-4" />
                {item.label}
              </Button>
            </Link>
          );
        })}
      </nav>

      {children}
    </div>
  );
}

export default function DashboardMarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <DashboardLayout>
      <MarketingProvider>
        <div className="mx-auto max-w-7xl space-y-6">
          <MarketingShell>{children}</MarketingShell>
        </div>
      </MarketingProvider>
    </DashboardLayout>
  );
}
