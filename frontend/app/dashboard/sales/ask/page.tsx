"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { Send, Sparkles, MessageSquare, Users } from "lucide-react";
import { toast } from "sonner";

import { useSalesVendor } from "@/components/sales/VendorContext";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

interface Customer {
  id: string;
  phone: string;
  name?: string;
  last_seen?: string;
}

interface OutboxMessage {
  id: string;
  phone: string;
  body: string;
  status: "sent" | "error";
  timestamp: Date;
}

interface CustomerResponse {
  customers: Customer[];
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function SalesAskAgentPage() {
  const { vendorId } = useSalesVendor();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loadingCustomers, setLoadingCustomers] = useState(true);
  const [selectedPhone, setSelectedPhone] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [outbox, setOutbox] = useState<OutboxMessage[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchCustomers = useCallback(
    async (signal?: AbortSignal) => {
      if (!vendorId) {
        setCustomers([]);
        setLoadingCustomers(false);
        return;
      }
      try {
        setLoadingCustomers(true);
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
        setError("Unable to load customer list.");
      } finally {
        setLoadingCustomers(false);
      }
    },
    [vendorId]
  );

  useEffect(() => {
    const controller = new AbortController();
    fetchCustomers(controller.signal);
    return () => controller.abort();
  }, [fetchCustomers]);

  useEffect(() => {
    if (customers.length === 0) {
      return;
    }
    if (!selectedPhone) {
      setSelectedPhone(customers[0].phone);
    }
  }, [customers, selectedPhone]);

  const customerOptions = useMemo(() => {
    return [...customers].sort((a, b) => (b.last_seen || "").localeCompare(a.last_seen || ""));
  }, [customers]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!vendorId) {
      toast.error("Select a vendor first.");
      return;
    }
    const phone = selectedPhone.trim();
    if (!phone) {
      toast.error("Add a customer phone number.");
      return;
    }
    if (!message.trim()) {
      toast.error("Write a message before sending.");
      return;
    }

    const outboxEntry: OutboxMessage = {
      id: crypto.randomUUID(),
      phone,
      body: message,
      status: "sent",
      timestamp: new Date(),
    };

    try {
      setSending(true);
      await axios.post(
        `${API_BASE}/api/vendors/${vendorId}/customers/${encodeURIComponent(phone)}/messages`,
        { text: message }
      );
      setOutbox((prev) => [outboxEntry, ...prev]);
      setMessage("");
      toast.success("Message queued for delivery", {
        description: `Sent to ${phone}`,
      });
    } catch (err) {
      setOutbox((prev) => [
        { ...outboxEntry, status: "error" },
        ...prev,
      ]);
      toast.error("Failed to send message", {
        description: axios.isAxiosError(err) ? err.response?.data?.detail ?? err.message : "Unknown error",
      });
    } finally {
      setSending(false);
    }
  };

  const handlePhoneChange = (value: string) => {
    setSelectedPhone(value);
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
      <Card className="border-2 border-slate-200 shadow-lg">
        <CardHeader className="space-y-2">
          <CardTitle className="flex items-center gap-2 text-xl text-[#174143]">
            <Sparkles className="h-5 w-5" />
            Ask the Sales Agent
          </CardTitle>
          <p className="text-sm text-slate-600">
            Send a manual WhatsApp reply on behalf of the AI agent. Responses are stored in the conversation history.
          </p>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">Customer phone</label>
              <Input
                value={selectedPhone}
                onChange={(event) => handlePhoneChange(event.target.value)}
                placeholder="e.g. +923001234567"
              />
              <p className="text-xs text-slate-500">
                Choose an existing conversation or type a new number to start a fresh thread.
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">Message body</label>
              <Textarea
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                minLength={1}
                rows={6}
                placeholder="Draft a helpful reply, e.g. Pricing details, stock confirmation, delivery updates"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Button type="submit" disabled={sending} className="bg-[#174143] text-white hover:bg-[#174143]/90">
                <Send className="mr-2 h-4 w-4" />
                {sending ? "Sending..." : "Send message"}
              </Button>
              <Badge variant="outline" className="border-slate-200 text-slate-500">
                Sent messages sync back to WhatsApp instantly
              </Badge>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card className="border-2 border-slate-200 shadow-lg">
        <CardHeader className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <CardTitle className="flex items-center gap-2 text-lg text-[#174143]">
            <Users className="h-4 w-4" />
            Quick fill from recent users
          </CardTitle>
          <Button variant="outline" size="sm" onClick={() => fetchCustomers()} disabled={loadingCustomers}>
            <MessageSquare className="mr-2 h-4 w-4" />
            Refresh list
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

          {loadingCustomers ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, index) => (
                <Skeleton key={index} className="h-10" />
              ))}
            </div>
          ) : customerOptions.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-200 p-6 text-center text-sm text-slate-500">
              No recent customers yet. Replies sent from here will create the conversation.
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {customerOptions.map((customer) => (
                <button
                  key={customer.id}
                  onClick={() => handlePhoneChange(customer.phone)}
                  type="button"
                  className="rounded-full border border-slate-200 px-4 py-2 text-sm transition hover:border-[#174143]/50 hover:bg-slate-50"
                >
                  <span className="font-medium text-slate-700">{customer.name || "Unnamed"}</span>
                  <span className="ml-2 text-xs text-slate-500">{customer.phone}</span>
                </button>
              ))}
            </div>
          )}

          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-slate-700">Sent messages</h3>
            {outbox.length === 0 ? (
              <p className="text-xs text-slate-500">Your outbound messages will appear here for quick auditing.</p>
            ) : (
              <div className="space-y-2">
                {outbox.map((entry) => (
                  <div
                    key={entry.id}
                    className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-medium">{entry.phone}</span>
                      <span className="text-xs text-slate-500">{formatTime(entry.timestamp)}</span>
                    </div>
                    <p className="mt-2 whitespace-pre-line text-sm">{entry.body}</p>
                    <Badge
                      className={
                        entry.status === "sent"
                          ? "mt-3 bg-emerald-100 text-emerald-700 border-emerald-200"
                          : "mt-3 bg-red-100 text-red-700 border-red-200"
                      }
                    >
                      {entry.status === "sent" ? "Delivered" : "Failed"}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
