"use client";

import type { ReactNode } from "react";

/**
 * Kept for the older /dashboard/sales, /dashboard/marketing and /dashboard/settings pages. The workspace layout above
 * them already supplies the shell (sidebar, top bar, tab bar), so this only passes its children through.
 */
export function DashboardLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
