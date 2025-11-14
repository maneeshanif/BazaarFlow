"use client";

import { createContext, useContext, useMemo } from "react";

import { useLocalStorage } from "@/hooks/use-local-storage";

interface SalesVendorContextValue {
  vendorId: string;
  setVendorId: (value: string) => void;
}

const SalesVendorContext = createContext<SalesVendorContextValue | undefined>(undefined);

export function SalesVendorProvider({ children }: { children: React.ReactNode }) {
  const [vendorId, setVendorId] = useLocalStorage<string>("bf.vendorId", "");
  const value = useMemo(() => ({ vendorId, setVendorId }), [vendorId, setVendorId]);
  return <SalesVendorContext.Provider value={value}>{children}</SalesVendorContext.Provider>;
}

export function useSalesVendor(): SalesVendorContextValue {
  const context = useContext(SalesVendorContext);
  if (!context) {
    throw new Error("useSalesVendor must be used within a SalesVendorProvider");
  }
  return context;
}
