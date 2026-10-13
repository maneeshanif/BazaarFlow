import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./global.css";
import { Toaster } from "@/components/ui/sonner";
import { LocaleProvider } from "@/lib/i18n/LocaleProvider";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "BazaarFlow - Agentic AI for Pakistan's Micro-Businesses",
  description: "Autonomous AI agents that handle WhatsApp orders, payments, inventory and marketing for small shops and freelancers.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {                                     
  return (
    <html lang="en" className={inter.variable}>
      <body className="antialiased">
        <LocaleProvider>
          {children}
          <Toaster position="top-right" richColors />
        </LocaleProvider>
      </body>
    </html>
  );
}
