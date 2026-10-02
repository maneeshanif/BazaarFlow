import type { ReactNode } from "react";
import { AuthProvider } from "@/lib/auth/AuthProvider";

export default function AppGroupLayout({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}
