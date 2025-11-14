"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { useRouter, useSearchParams } from "next/navigation";
import { Clock, MessageCircle, RefreshCw, Users } from "lucide-react";

import { useSalesVendor } from "@/components/sales/VendorContext";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

interface Customer {
  id: string;
  phone: string;
  name?: string;
  last_seen?: string;
}

interface Message {
  id: string;
  direction: "inbound" | "outbound" | string;
  text?: string | null;
  timestamp?: string;
}

interface CustomerResponse {
  customers: Customer[];
}

interface MessagesResponse {
  messages: Message[];
}

function formatTimestamp(timestamp?: string): string {
  if (!timestamp) {
    return "Unknown";
  }
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }
  return date.toLocaleString();
}

export default function SalesHistoryPage() {
  const { vendorId } = useSalesVendor();
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialCustomerPhone = searchParams.get("customer") || "";

  const [customers, setCustomers] = useState<Customer[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedPhone, setSelectedPhone] = useState(initialCustomerPhone);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messagesError, setMessagesError] = useState<string | null>(null);

  const fetchCustomers = useCallback(
    async (signal?: AbortSignal) => {
      if (!vendorId) {
        setCustomers([]);
        setLoadingList(false);
        return;
      }
      try {
        setLoadingList(true);
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
        setLoadingList(false);
      }
    },
    [vendorId]
  );

  const fetchMessages = useCallback(
    async (phone: string, signal?: AbortSignal) => {
      if (!vendorId || !phone) {
        setMessages([]);
        setLoadingMessages(false);
        return;
      }
      try {
        setLoadingMessages(true);
        setMessagesError(null);
        const { data } = await axios.get<MessagesResponse>(
          `${API_BASE}/api/vendors/${vendorId}/customers/${encodeURIComponent(phone)}/messages`,
          { signal }
        );
        setMessages((data.messages || []).sort((a, b) => (a.timestamp || "").localeCompare(b.timestamp || "")));
      } catch (err) {
        if (axios.isCancel(err)) {
          return;
        }
        setMessagesError("Unable to load messages for this contact.");
        setMessages([]);
      } finally {
        setLoadingMessages(false);
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
    if (!selectedPhone) {
      setMessages([]);
      return;
    }
    const controller = new AbortController();
    fetchMessages(selectedPhone, controller.signal);
    return () => controller.abort();
  }, [fetchMessages, selectedPhone]);

  useEffect(() => {
    if (!initialCustomerPhone) {
      return;
    }
    setSelectedPhone(initialCustomerPhone);
  }, [initialCustomerPhone]);

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

  const handleSelect = (phone: string) => {
    setSelectedPhone(phone);
    router.replace(`/dashboard/sales/history?customer=${encodeURIComponent(phone)}`);
  };

  return (
    <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
      <Card className="h-full border-2 border-slate-200 shadow-md">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg text-[#174143]">
            <Users className="h-4 w-4" />
            Conversation List
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2">
            <Input
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Search contacts"
            />
            <Button variant="outline" size="icon" onClick={() => fetchCustomers()} disabled={loadingList}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
          {error && <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}

          {loadingList ? (
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <Skeleton key={index} className="h-12" />
              ))}
            </div>
          ) : filteredCustomers.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-2 py-10 text-center text-slate-500">
              <MessageCircle className="h-8 w-8 text-[#174143]/60" />
              <p>No conversations yet.</p>
              <p className="text-xs">New chats appear here automatically.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredCustomers.map((customer) => {
                const isActive = customer.phone === selectedPhone;
                return (
                  <button
                    key={customer.id}
                    onClick={() => handleSelect(customer.phone)}
                    className={cn(
                      "w-full rounded-lg border p-3 text-left transition",
                      isActive
                        ? "border-[#174143] bg-[#174143]/10 text-[#174143]"
                        : "border-slate-200 hover:border-[#174143]/40 hover:bg-slate-50"
                    )}
                  >
                    <p className="text-sm font-medium">{customer.name || customer.phone}</p>
                    <p className="text-xs text-slate-500">{customer.phone}</p>
                    {customer.last_seen && (
                      <p className="text-xs text-slate-400">Last seen {formatTimestamp(customer.last_seen)}</p>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="min-h-[520px] border-2 border-slate-200 shadow-md">
        <CardHeader className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle className="text-lg text-[#174143]">
              {selectedPhone ? `Conversation with ${selectedPhone}` : "Pick a customer"}
            </CardTitle>
            {selectedPhone && (
              <p className="text-sm text-slate-500">
                Messages pulled from the JSON data store. Updates automatically when new events arrive.
              </p>
            )}
          </div>
          {selectedPhone && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchMessages(selectedPhone)}
              disabled={loadingMessages}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Sync now
            </Button>
          )}
        </CardHeader>
        <CardContent className="flex h-full flex-col gap-4">
          {!selectedPhone ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 text-slate-500">
              <MessageCircle className="h-10 w-10 text-[#174143]/60" />
              <p className="text-lg font-medium">Select a conversation to view the transcript.</p>
            </div>
          ) : loadingMessages ? (
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <Skeleton key={index} className="h-16" />
              ))}
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 text-slate-500">
              <MessageCircle className="h-10 w-10 text-[#174143]/60" />
              <p className="text-lg font-medium">No messages yet</p>
              <p className="text-sm max-w-sm text-center">
                We have not received any conversation logs for this customer. Messages sent from WhatsApp will appear here instantly.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message) => {
                const outbound = message.direction === "outbound";
                return (
                  <div key={message.id} className="flex flex-col">
                    <div
                      className={cn(
                        "w-fit max-w-2xl rounded-2xl px-4 py-3 text-sm shadow-sm",
                        outbound
                          ? "ml-auto bg-[#174143] text-white"
                          : "bg-slate-100 text-slate-900"
                      )}
                    >
                      <p className="whitespace-pre-line">{message.text || "(no text)"}</p>
                    </div>
                    <div className={cn("mt-1 flex items-center gap-2 text-xs", outbound ? "justify-end" : "text-slate-500")}
                    >
                      <Badge variant="outline" className="border-slate-200 text-slate-500">
                        {outbound ? "Agent" : "Customer"}
                      </Badge>
                      <div className="flex items-center gap-1 text-slate-400">
                        <Clock className="h-3 w-3" />
                        {formatTimestamp(message.timestamp)}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {messagesError && (
            <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{messagesError}</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
