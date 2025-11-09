import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./global.css";
import Header from "./components/Header";
import Image from "next/image";
import SmoothScroll from "@/components/SmoothScroll";

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
        <SmoothScroll />
        <Header />

        <main className="site-main">{children}</main>

        <footer className="border-t border-[#427A76]/30 bg-gradient-to-br from-[#174143] via-[#427A76] to-[#174143]">
          <div className="container mx-auto py-12">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
              <div>
                <Image src="/logo.jpeg" alt="BazaarFlow" className="h-10 w-auto mb-4 rounded-lg ring-2 ring-white/30" width={120} height={40} priority />
                <p className="text-sm text-[rgb(var(--muted))]">Agentic AI for Pakistan&apos;s informal digital economy.</p>
              </div>
              <div>
                <h4 className="font-semibold mb-4 text-white">Product</h4>
                <div className="space-y-2">
                  <a href="/agents" className="block text-sm text-[rgb(var(--muted))] hover:text-white transition-colors">Agents</a>
                  <a href="/demo" className="block text-sm text-[rgb(var(--muted))] hover:text-white transition-colors">Demo</a>
                </div>
              </div>
              <div>
                <h4 className="font-semibold mb-4 text-white">Company</h4>
                <div className="space-y-2">
                  <a href="/about" className="block text-sm text-[rgb(var(--muted))] hover:text-white transition-colors">About</a>
                  <a href="/contact" className="block text-sm text-[rgb(var(--muted))] hover:text-white transition-colors">Contact</a>
                </div>
              </div>
              <div>
                <h4 className="font-semibold mb-4 text-white">Contact</h4>
                <a href="mailto:hello@bazaarflow.example" className="block text-sm text-[rgb(var(--muted))] hover:text-white transition-colors mb-4">
                  hello@bazaarflow.example
                </a>
                <p className="text-sm text-[rgb(var(--muted))]/70">© {new Date().getFullYear()} BazaarFlow</p>
              </div>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
