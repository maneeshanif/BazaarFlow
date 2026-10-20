import type { Metadata } from "next";
import { Anton, Inter_Tight, Nothing_You_Could_Do } from "next/font/google";
import "./global.css";
import { Toaster } from "@/components/ui/sonner";
import { LocaleProvider } from "@/lib/i18n/LocaleProvider";
import { ArcTransition } from "@/components/brand/ArcTransition";

const body = Inter_Tight({ subsets: ["latin"], variable: "--font-body", display: "swap" });
const display = Anton({ subsets: ["latin"], weight: "400", variable: "--font-display", display: "swap" });
const slip = Nothing_You_Could_Do({ subsets: ["latin"], weight: "400", variable: "--font-slip", display: "swap" });

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
    <html lang="en" className={`${body.variable} ${display.variable} ${slip.variable}`}>
      <body className="antialiased">
        <LocaleProvider>
          {children}
          <ArcTransition />
          <Toaster position="top-right" richColors />
        </LocaleProvider>
      </body>
    </html>
  );
}
