import type { ReactNode } from "react";
import { AuthProvider } from "@/lib/auth/AuthProvider";

/** Sign-in and sign-up share one session provider and none of the marketing chrome. */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}
