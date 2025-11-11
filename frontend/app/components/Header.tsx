"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Menu, X, ChevronDown, MessageSquare, Package, DollarSign, BarChart3, Megaphone } from "lucide-react";

export default function Header() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [agentDropdownOpen, setAgentDropdownOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined") {
      document.body.style.overflow = open ? "hidden" : "";
    }
    return () => {
      if (typeof window !== "undefined") document.body.style.overflow = "";
    };
  }, [open]);

  const navLinks = [
    { href: "/", label: "Home" },
    { href: "/agents", label: "Agents" },
    { href: "/demo", label: "Demo" },
    { href: "/logs", label: "Logs" },
    { href: "/about", label: "About" },
  ];

  const agentChatLinks = [
    { href: "/chat/sales", label: "Sales", icon: MessageSquare },
    { href: "/chat/inventory", label: "Inventory", icon: Package },
    { href: "/chat/finance", label: "Finance", icon: DollarSign },
    { href: "/chat/analytics", label: "Analytics", icon: BarChart3 },
    { href: "/chat/marketing", label: "Marketing", icon: Megaphone },
  ];

  return (
    <motion.header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-gradient-to-r from-[#174143] via-[#427A76] to-[#174143] backdrop-blur-lg border-b border-[#427A76]/30 shadow-lg"
          : "bg-gradient-to-r from-[#174143]/95 via-[#427A76]/95 to-[#174143]/95 backdrop-blur-sm"
      }`}
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16 md:h-20">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 group">
            <motion.div
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Image
                src="/logo.jpeg"
                alt="BazaarFlow"
                width={40}
                height={40}
                className="rounded-lg ring-2 ring-white/30"
              />
            </motion.div>
            <span className="font-bold text-xl hidden sm:block text-white group-hover:text-[rgb(var(--muted))] transition-colors">
              BazaarFlow
            </span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`relative px-4 py-2 text-sm font-medium transition-colors ${
                  pathname === link.href
                    ? "text-[rgb(var(--muted))]"
                    : "hover:text-[rgb(var(--muted))] text-white"
                }`}
              >
                {link.label}
                {pathname === link.href && (
                  <motion.div
                    layoutId="navbar-indicator"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-white"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
              </Link>
            ))}

            {/* Agent Chat Dropdown */}
            <div
              className="relative"
              onMouseEnter={() => setAgentDropdownOpen(true)}
              onMouseLeave={() => setAgentDropdownOpen(false)}
            >
              <button
                className={`relative px-4 py-2 text-sm font-medium transition-colors flex items-center gap-1 ${
                  pathname.startsWith("/chat")
                    ? "text-white"
                    : "text-[rgb(var(--muted))] hover:text-white"
                }`}
              >
                Chat Agents
                <ChevronDown className="w-3 h-3" />
                {pathname.startsWith("/chat") && (
                  <motion.div
                    layoutId="navbar-indicator"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-white"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
              </button>

              <AnimatePresence>
                {agentDropdownOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    transition={{ duration: 0.2 }}
                    className="absolute top-full left-0 mt-2 w-48 bg-white rounded-lg shadow-xl border border-slate-200 overflow-hidden z-50"
                  >
                    {agentChatLinks.map((link) => {
                      const Icon = link.icon;
                      return (
                        <Link
                          key={link.href}
                          href={link.href}
                          className="flex items-center gap-3 px-4 py-3 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                        >
                          <Icon className="w-4 h-4" />
                          {link.label}
                        </Link>
                      );
                    })}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </nav>

          {/* Right Side */}
          <div className="hidden md:flex items-center gap-4">
            {/* Theme Toggle */}
            <ThemeToggle />

            {/* Agent Status */}
            <div className="flex items-center gap-2 bg-white/10 px-3 py-1.5 rounded-full border border-white/20">
              {[
                { name: "Sales", color: "bg-white" },
                { name: "Inventory", color: "bg-white" },
                { name: "Analytics", color: "bg-white" },
              ].map((agent, i) => (
                <motion.div
                  key={agent.name}
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: i * 0.1 }}
                  title={agent.name}
                  className="relative"
                >
                  <div className={`w-2 h-2 rounded-full ${agent.color} animate-pulse shadow-lg shadow-white/50`} />
                </motion.div>
              ))}
              <span className="text-xs text-white ml-1 font-medium">Agents Active</span>
            </div>

            <Button asChild size="sm" variant="outline" className="border-2 border-white text-slate-300 hover:bg-white/10 font-semibold">
              <Link href="/dashboard">Dashboard</Link>
            </Button>

            <Button asChild size="sm" className="bg-white text-[#174143] hover:bg-[rgb(var(--muted))] font-semibold shadow-lg">
              <Link href="/sales">Get Started</Link>
            </Button>
          </div>

          {/* Mobile Menu Button & Theme Toggle */}
          <div className="md:hidden flex items-center gap-2">
            <ThemeToggle />
            <button
              onClick={() => setOpen(!open)}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors text-white"
              aria-label="Toggle menu"
            >
              {open ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="md:hidden border-t border-white/20 bg-[#174143]/98 backdrop-blur-lg"
          >
            <nav className="container mx-auto px-4 py-6 space-y-4">
              {navLinks.map((link, i) => (
                <motion.div
                  key={link.href}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 }}
                >
                  <Link
                    href={link.href}
                    onClick={() => setOpen(false)}
                    className={`block px-4 py-3 rounded-lg font-medium transition-colors ${
                      pathname === link.href
                        ? "bg-white text-[#174143]"
                        : "text-[rgb(var(--muted))] hover:bg-white/10"
                    }`}
                  >
                    {link.label}
                  </Link>
                </motion.div>
              ))}

              {/* Agent Chat Links */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: navLinks.length * 0.1 }}
                className="border-t border-white/20 pt-4"
              >
                <p className="text-xs text-[rgb(var(--muted))] px-4 mb-2 font-semibold">Chat with Agents</p>
                {agentChatLinks.map((link) => {
                  const Icon = link.icon;
                  return (
                    <Link
                      key={link.href}
                      href={link.href}
                      onClick={() => setOpen(false)}
                      className={`flex items-center gap-3 px-4 py-2 rounded-lg font-medium transition-colors ${
                        pathname === link.href
                          ? "bg-white text-[#174143]"
                          : "text-[rgb(var(--muted))] hover:bg-white/10"
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      {link.label}
                    </Link>
                  );
                })}
              </motion.div>

              {/* Mobile Action Buttons */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: (navLinks.length + 1) * 0.1 }}
                className="space-y-3 pt-4 border-t border-white/20"
              >
                <Button asChild variant="outline" className="w-full border-2 border-white text-white hover:bg-white/10">
                  <Link href="/dashboard" onClick={() => setOpen(false)}>
                    Dashboard
                  </Link>
                </Button>
                <Button asChild className="w-full bg-white text-[#174143] hover:bg-[rgb(var(--muted))]">
                  <Link href="/sales" onClick={() => setOpen(false)}>
                    Get Started
                  </Link>
                </Button>
              </motion.div>
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  );
}
