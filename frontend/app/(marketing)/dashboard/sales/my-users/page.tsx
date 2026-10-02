"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { useRouter } from "next/navigation";
import { Users, RefreshCw, Phone, Clock, ArrowRight } from "lucide-react";

import { useSalesVendor } from "@/components/sales/VendorContext";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

interface Customer {
  id: string;
  phone: string;
  name?: string;
  first_seen?: string;
  last_seen?: string;
}

interface CustomerResponse {
  customers: Customer[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

function formatTimestamp(timestamp?: string): string {
  if (!timestamp) {
    return "No activity yet";
  }
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }
  return date.toLocaleString();
}

function customerStatus(timestamp?: string): { label: string; className: string } {
  if (!timestamp) {
    return { label: "New lead", className: "bg-slate-100 text-slate-600 border-slate-200" };
  }
  const seenAt = new Date(timestamp).getTime();
  const diffMinutes = (Date.now() - seenAt) / 60000;
  if (diffMinutes <= 60) {
    return { label: "Active", className: "bg-emerald-100 text-emerald-700 border-emerald-200" };
  }
  if (diffMinutes <= 720) {
    return { label: "Recent", className: "bg-sky-100 text-sky-700 border-sky-200" };
  }
  return { label: "Dormant", className: "bg-slate-100 text-slate-600 border-slate-200" };
}

export default function SalesMyUsersPage() {
  const { vendorId } = useSalesVendor();
  const router = useRouter();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCustomers = useCallback(
    async (signal?: AbortSignal) => {
      if (!vendorId) {
        setCustomers([]);
        setLoading(false);
        return;
      }
      try {
        setLoading(true);
        setError(null);
        const { data } = await axios.get<CustomerResponse>(
          `${API_BASE}/api/vendors/${vendorId}/customers`,
          { signal }
        );
        setCustomers(data.customers || []);
      } catch (err) {
        if (axios.isCancel(err)) {
          return;
        }
        setError("Unable to load customers. Please try again.");
      } finally {
        setLoading(false);
      }
    },
    [vendorId]
  );

  useEffect(() => {
    const controller = new AbortController();
    fetchCustomers(controller.signal);
    return () => controller.abort();
  }, [fetchCustomers]);

  const filteredCustomers = useMemo(() => {
    const needle = searchTerm.trim().toLowerCase();
    return [...customers]
      .sort((a, b) => (b.last_seen || "").localeCompare(a.last_seen || ""))
      .filter((customer) => {
        if (!needle) {
          return true;
        }
        return (
          customer.phone.toLowerCase().includes(needle) ||
          (customer.name?.toLowerCase().includes(needle) ?? false)
        );
      });
  }, [customers, searchTerm]);

  const handleRefresh = () => {
    setSearchTerm("");
    fetchCustomers();
  };

  return (
    <div className="space-y-6">
      <Card className="border-2 border-slate-200 shadow-lg">
        <CardHeader className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-xl font-semibold text-[#174143]">
              <Users className="h-5 w-5" />
              Customer Directory
            </CardTitle>
            <p className="text-sm text-slate-600">
              Track every WhatsApp contact linked to this vendor.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="relative w-full sm:w-64">
              <Input
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Search by name or phone"
                className="pl-10"
              />
              <Phone className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            </div>
            <Button onClick={handleRefresh} variant="outline" disabled={loading}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              {error}
            </div>
          )}

          {loading ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <Skeleton key={index} className="h-32" />
              ))}
            </div>
          ) : filteredCustomers.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 py-12 text-center text-slate-500">
              <Users className="h-10 w-10 text-[#174143]/60" />
              <p className="text-lg font-medium">No customers found</p>
              <p className="text-sm max-w-md">
                Conversations appear here once a customer messages your WhatsApp Business number.
              </p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {filteredCustomers.map((customer) => {
                const status = customerStatus(customer.last_seen);
                return (
                  <Card key={customer.id} className="border border-slate-200 shadow-sm">
                    <CardContent className="flex h-full flex-col justify-between gap-4 p-5">
                      <div className="space-y-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-semibold text-slate-900">
                              {customer.name || "Unnamed contact"}
                            </p>
                            <p className="text-xs text-slate-500">{customer.phone}</p>
                          </div>
                          <Badge className={status.className}>{status.label}</Badge>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-slate-500">
                          <Clock className="h-4 w-4" />
                          Last seen: {formatTimestamp(customer.last_seen)}
                        </div>
                      </div>
                      <Button
                        variant="secondary"
                        className="bg-[#174143] text-white hover:bg-[#174143]/90"
                        onClick={() => router.push(`/dashboard/sales/history?customer=${encodeURIComponent(customer.phone)}`)}
                      >
                        View conversation
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </Button>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
