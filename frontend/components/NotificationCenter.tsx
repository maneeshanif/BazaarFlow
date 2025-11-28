"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Bell, Loader2, AlertTriangle, CheckCircle2, XCircle } from "lucide-react";

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

interface NotificationRecord {
  id: number;
  type: string;
  title: string;
  message: string;
  severity: "info" | "warning" | "error" | string;
  created_at: string;
  read: boolean;
  metadata?: Record<string, unknown>;
}

interface ApiListResponse {
  ok: boolean;
  notifications: NotificationRecord[];
  unread: number;
}

function formatDate(iso: string): string {
  try {
    const date = new Date(iso);
    return date.toLocaleString();
  } catch {
    return iso;
  }
}

function severityBadgeClasses(severity: string): string {
  if (severity === "error") {
    return "bg-red-100 text-red-700 border-red-200";
  }
  if (severity === "warning") {
    return "bg-amber-100 text-amber-800 border-amber-200";
  }
  return "bg-slate-100 text-slate-700 border-slate-200";
}

function severityIcon(severity: string) {
  if (severity === "error") return <XCircle className="w-3 h-3 mr-1" />;
  if (severity === "warning") return <AlertTriangle className="w-3 h-3 mr-1" />;
  return <CheckCircle2 className="w-3 h-3 mr-1" />;
}

export function NotificationCenter() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [markingAll, setMarkingAll] = useState(false);
  const [items, setItems] = useState<NotificationRecord[]>([]);
  const [unread, setUnread] = useState(0);

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
      const res = await fetch(`${base}/api/notifications`);
      if (!res.ok) {
        throw new Error("Failed to fetch notifications");
      }
      const data = (await res.json()) as ApiListResponse;
      if (data.ok) {
        setItems(data.notifications || []);
        setUnread(data.unread || 0);
      }
    } catch (err) {
      console.error("Failed to load notifications", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Load on mount so the badge count is ready
    void fetchNotifications();
  }, []);

  const handleOpenChange = (value: boolean) => {
    setOpen(value);
    if (value) {
      void fetchNotifications();
    }
  };

  const handleMarkAllRead = async () => {
    setMarkingAll(true);
    try {
      const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
      const res = await fetch(`${base}/api/notifications/read-all`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Failed to mark all read");
      // Optimistically update local state
      setItems((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnread(0);
    } catch (err) {
      console.error("Failed to mark all notifications read", err);
    } finally {
      setMarkingAll(false);
    }
  };

  const handleOpenInventoryForNotification = (n: NotificationRecord) => {
    const metadata = (n.metadata ?? {}) as {
      sku?: string;
      new_stock?: number;
      reorder_point?: number;
      bucket_from?: string;
      bucket_to?: string;
    };
    const sku = metadata.sku;
    if (sku) {
      router.push(`/dashboard/inventory?sku=${encodeURIComponent(sku)}`);
    } else {
      router.push("/dashboard/inventory");
    }
    setOpen(false);
  };

  const hasNotifications = items.length > 0;

  return (
    <div className="flex items-center gap-3">
      <Dialog open={open} onOpenChange={handleOpenChange}>
        <Button
          variant="outline"
          size="icon"
          className="relative rounded-full border-slate-200 dark:border-slate-700"
          onClick={() => handleOpenChange(true)}
        >
          <Bell className="w-5 h-5" />
          {unread > 0 && (
            <span className="absolute -top-1 -right-1 inline-flex items-center justify-center rounded-full bg-red-600 text-white text-[10px] min-w-[18px] h-[18px] px-1">
              {unread > 9 ? "9+" : unread}
            </span>
          )}
        </Button>

        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Notifications</DialogTitle>
            <DialogDescription>
              Inventory alerts and system events that need your attention.
            </DialogDescription>
          </DialogHeader>

          {loading ? (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="w-6 h-6 animate-spin text-[#174143]" />
            </div>
          ) : !hasNotifications ? (
            <div className="py-8 text-center text-sm text-slate-500 dark:text-slate-400">
              No notifications yet. As inventory falls below reorder points, alerts will appear here.
            </div>
          ) : (
            <div className="space-y-3 max-h-[400px] overflow-y-auto">
              {items.map((n) => (
                <Card
                  key={n.id}
                  className={`border ${
                    n.read
                      ? "border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900"
                      : "border-amber-200 bg-amber-50 dark:border-amber-500/60 dark:bg-slate-900"
                  }`}
                >
                  <CardContent className="p-4 flex flex-col gap-2">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <Badge
                            variant="outline"
                            className={`${severityBadgeClasses(n.severity)} flex items-center gap-1`}
                          >
                            {severityIcon(n.severity)}
                            <span className="capitalize text-xs">{n.severity || "info"}</span>
                          </Badge>
                          {!n.read && (
                            <span className="inline-flex w-2 h-2 rounded-full bg-amber-500" aria-hidden="true" />
                          )}
                        </div>
                        <p className="font-medium text-sm text-slate-900 dark:text-white">
                          {n.title}
                        </p>
                        <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                          {n.message}
                        </p>
                      </div>
                      <span className="text-[11px] text-slate-500 dark:text-slate-400 whitespace-nowrap">
                        {formatDate(n.created_at)}
                      </span>
                    </div>

                    {n.metadata && typeof n.metadata === "object" && (() => {
                      const meta = (n.metadata ?? {}) as {
                        sku?: string;
                        new_stock?: number;
                        reorder_point?: number;
                        bucket_from?: string;
                        bucket_to?: string;
                      };
                      const { sku, new_stock, reorder_point, bucket_from, bucket_to } = meta;
                      if (
                        sku === undefined &&
                        new_stock === undefined &&
                        reorder_point === undefined &&
                        bucket_from === undefined &&
                        bucket_to === undefined
                      ) {
                        return null;
                      }
                      return (
                      <div className="mt-1 grid grid-cols-2 gap-2 text-[11px] text-slate-600 dark:text-slate-400">
                        {sku !== undefined && (
                          <div>
                            <span className="font-semibold">SKU:</span> {sku}
                          </div>
                        )}
                        {new_stock !== undefined && (
                          <div>
                            <span className="font-semibold">Stock now:</span> {new_stock}
                          </div>
                        )}
                        {reorder_point !== undefined && (
                          <div>
                            <span className="font-semibold">Reorder at:</span> {reorder_point}
                          </div>
                        )}
                        {bucket_from !== undefined && bucket_to !== undefined && (
                          <div>
                            <span className="font-semibold">Bucket:</span> {bucket_from} → {bucket_to}
                          </div>
                        )}
                      </div>
                      );
                    })()}

                    <div className="mt-2 flex justify-end">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleOpenInventoryForNotification(n)}
                      >
                        View in inventory
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          <DialogFooter className="mt-4 flex items-center justify-between">
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {unread === 0
                ? "You're all caught up."
                : `${unread} unread notification${unread === 1 ? "" : "s"}.`}
            </p>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={unread === 0 || markingAll}
              onClick={() => void handleMarkAllRead()}
            >
              {markingAll && <Loader2 className="w-3 h-3 mr-1 animate-spin" />}
              Mark all as read
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
