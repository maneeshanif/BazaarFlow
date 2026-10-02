import type { ReactNode } from "react";
import { AuthProvider } from "@/lib/auth/AuthProvider";

export default function SignInLayout({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}
