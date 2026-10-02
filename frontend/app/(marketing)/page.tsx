"use client";

import { useMemo, useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { motion, useScroll, useTransform, useMotionValue, useSpring } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MeridianCards } from "@/components/MeridianCards";
import {
  ArrowRight, MessageSquare, Package, TrendingUp, Sparkles,
  CheckCircle2, BarChart3, Users, Zap, Shield, Globe,
  Smartphone, DollarSign, Clock, Star, ChevronRight
} from "lucide-react";

const fadeInUp = {
  initial: { opacity: 0, y: 60 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] }
};

const staggerContainer = {
  animate: {
    transition: {
      staggerChildren: 0.1
    }
  }
};

export default function Home() {
  const { scrollYProgress } = useScroll();
  const y = useTransform(scrollYProgress, [0, 1], [0, -50]);

  // Mouse position tracking
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  // Generate star positions once
  const stars = useMemo(() => {
    return [...Array(50)].map((_, i) => ({
      x: (i * 37) % 100, // Pseudo-random but deterministic
      y: (i * 73) % 100,
      delay: (i * 0.13) % 3,
      duration: 2 + (i % 3),
    }));
  }, []);

  // Track mouse movement
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePos({ x: e.clientX, y: e.clientY });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <main className="min-h-screen w-full overflow-hidden bg-white">
      {/* Hero Section - Mission Control Style */}
      <section className="relative min-h-screen flex items-center justify-center px-4 py-32 overflow-hidden">
        {/* Animated gradient background */}
        <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-blue-50/30" />

        {/* Animated grid/mesh background */}
        <div className="absolute inset-0">
          {/* Horizontal lines */}
          {[...Array(20)].map((_, i) => {
            const lineY = (i * 5);
            const lineYPx = (lineY / 100) * (typeof window !== 'undefined' ? window.innerHeight : 1000);
            const distance = Math.abs(mousePos.y - lineYPx);
            const maxDistance = 200;
            const opacity = Math.max(0.2, 1 - (distance / maxDistance));
            const glowOpacity = Math.max(0, 0.8 - (distance / (maxDistance / 2)));

            return (
              <motion.div
                key={`h-${i}`}
                className="absolute left-0 right-0 h-px transition-opacity duration-200"
                style={{
                  top: `${lineY}%`,
                  background: 'linear-gradient(to right, transparent, rgb(226, 232, 240), transparent)',
                  opacity: opacity
                }}
              >
                <div
                  className="absolute inset-0 bg-gradient-to-r from-transparent via-[#427A76] to-transparent transition-opacity duration-200"
                  style={{ opacity: glowOpacity }}
                />
              </motion.div>
            );
          })}
          {/* Vertical lines */}
          {[...Array(20)].map((_, i) => {
            const lineX = (i * 5);
            const lineXPx = (lineX / 100) * (typeof window !== 'undefined' ? window.innerWidth : 1000);
            const distance = Math.abs(mousePos.x - lineXPx);
            const maxDistance = 200;
            const opacity = Math.max(0.2, 1 - (distance / maxDistance));
            const glowOpacity = Math.max(0, 0.8 - (distance / (maxDistance / 2)));

            return (
              <motion.div
                key={`v-${i}`}
                className="absolute top-0 bottom-0 w-px transition-opacity duration-200"
                style={{
                  left: `${lineX}%`,
                  background: 'linear-gradient(to bottom, transparent, rgb(226, 232, 240), transparent)',
                  opacity: opacity
                }}
              >
                <div
                  className="absolute inset-0 bg-gradient-to-b from-transparent via-[#427A76] to-transparent transition-opacity duration-200"
                  style={{ opacity: glowOpacity }}
                />
              </motion.div>
            );
          })}
        </div>

        {/* Pulsing stars/dots at grid intersections */}
        <div className="absolute inset-0">
          {stars.map((star, i) => (
            <motion.div
              key={`star-${i}`}
              className="absolute w-1 h-1 bg-[#427A76] rounded-full"
              style={{
                left: `${star.x}%`,
                top: `${star.y}%`,
                boxShadow: '0 0 10px rgba(66, 122, 118, 0.5)'
              }}
              animate={{
                opacity: [0, 1, 0],
                scale: [0, 1.5, 0],
              }}
              transition={{
                duration: star.duration,
                repeat: Infinity,
                delay: star.delay,
                ease: "easeInOut"
              }}
            />
          ))}
        </div>

        {/* Floating gradient orbs */}
        <motion.div
          className="absolute top-20 left-10 w-72 h-72 bg-gradient-to-br from-[#174143]/10 to-[#427A76]/10 rounded-full blur-3xl"
          animate={{ y: [0, 30, 0], scale: [1, 1.1, 1] }}
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute bottom-20 right-10 w-96 h-96 bg-gradient-to-br from-blue-400/10 to-purple-400/10 rounded-full blur-3xl"
          animate={{ y: [0, -30, 0], scale: [1.1, 1, 1.1] }}
          transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
        />
        
        <div className="container mx-auto relative z-10 max-w-7xl">
          <motion.div
            initial="initial"
            animate="animate"
            variants={staggerContainer}
            className="text-center space-y-8 max-w-5xl mx-auto"
          >
            <motion.div variants={fadeInUp} className="inline-block">
              <Badge className="px-6 py-3 text-sm bg-gradient-to-r from-[#174143] to-[#427A76] text-white border-0 font-medium shadow-lg hover:shadow-xl transition-all">
                <Sparkles className="w-4 h-4 mr-2" />
                Agentic AI Platform for Pakistan&apos;s Digital Economy
              </Badge>
            </motion.div>

            <motion.h1
              variants={fadeInUp}
              className="text-6xl md:text-7xl lg:text-8xl font-bold leading-[1.1] tracking-tight"
            >
              <span className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 bg-clip-text text-transparent">
                Autonomous AI Agents
              </span>
              <br />
              <span className="relative inline-block mt-2">
                <span className="bg-gradient-to-r from-[#174143] via-[#427A76] to-blue-600 bg-clip-text text-transparent">
                  for Your Business
                </span>
                <motion.span
                  className="absolute -inset-2 bg-gradient-to-r from-[#174143]/20 via-[#427A76]/20 to-blue-600/20 blur-3xl -z-10"
                  animate={{ opacity: [0.4, 0.6, 0.4] }}
                  transition={{ duration: 3, repeat: Infinity }}
                />
              </span>
            </motion.h1>

            <motion.p
              variants={fadeInUp}
              className="text-xl md:text-2xl text-slate-700 font-medium max-w-3xl mx-auto leading-relaxed drop-shadow-sm"
            >
              Multi-agent AI system that handles WhatsApp orders, payments, inventory,
              and marketing — built for Pakistan&apos;s 80% informal economy
            </motion.p>

            <motion.div
              variants={fadeInUp}
              className="flex flex-wrap gap-4 justify-center pt-6"
            >
              <motion.div whileHover={{ scale: 1.05, y: -2 }} whileTap={{ scale: 0.98 }}>
                <Button asChild size="lg" className="h-14 px-8 text-base font-semibold bg-gradient-to-r from-[#174143] to-[#427A76] hover:from-[#427A76] hover:to-[#174143] text-white shadow-[0_10px_40px_-10px_rgba(23,65,67,0.4)] hover:shadow-[0_20px_50px_-10px_rgba(23,65,67,0.5)] transition-all group">
                  <Link href="/sales">
                    Start Free Trial
                    <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
                  </Link>
                </Button>
              </motion.div>
              <motion.div whileHover={{ scale: 1.05, y: -2 }} whileTap={{ scale: 0.98 }}>
                <Button asChild size="lg" variant="outline" className="h-14 px-8 text-base font-semibold border-2 border-slate-300 hover:border-[#174143] hover:bg-slate-50 transition-all">
                  <Link href="/demo">
                    Watch Demo
                    <ChevronRight className="ml-1 w-5 h-5" />
                  </Link>
                </Button>
              </motion.div>
            </motion.div>

            <motion.div
              variants={fadeInUp}
              className="flex items-center justify-center gap-8 pt-8 text-sm text-slate-500"
            >
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#427A76]" />
                <span>No credit card required</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#427A76]" />
                <span>14-day free trial</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#427A76]" />
                <span>Cancel anytime</span>
              </div>
            </motion.div>
          </motion.div>
        </div>

        {/* Scroll indicator */}
        <motion.div
          className="absolute bottom-8 left-1/2 -translate-x-1/2"
          animate={{ y: [0, 10, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <div className="w-6 h-10 border-2 border-slate-300 rounded-full flex justify-center pt-2">
            <motion.div
              className="w-1.5 h-1.5 bg-slate-400 rounded-full"
              animate={{ y: [0, 12, 0] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
          </div>
        </motion.div>
      </section>

      {/* Problem Section */}
      <section className="py-24 px-4 bg-slate-50">
        <div className="container mx-auto max-w-6xl">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl md:text-5xl font-bold text-slate-900 mb-6">
              The Challenge
            </h2>
            <p className="text-xl text-slate-600 max-w-3xl mx-auto">
              Over 80% of Pakistan&apos;s economy operates informally. Small shops, freelancers, 
              and local service providers juggle WhatsApp orders, Easypaisa payments, and Facebook 
              pages manually — without sophisticated business tools.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              { icon: Smartphone, title: "Manual Operations", desc: "Managing orders across WhatsApp, calls, and messages", color: "from-slate-600 to-slate-700", bg: "bg-slate-50", border: "border-slate-200" },
              { icon: DollarSign, title: "Payment Chaos", desc: "Tracking Easypaisa, JazzCash, and cash payments manually", color: "from-slate-600 to-slate-700", bg: "bg-slate-50", border: "border-slate-200" },
              { icon: Clock, title: "Time Consuming", desc: "Hours spent on inventory, receipts, and customer follow-ups", color: "from-slate-600 to-slate-700", bg: "bg-slate-50", border: "border-slate-200" },
            ].map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                whileHover={{ y: -4 }}
                className={`bg-white p-8 rounded-2xl border-2 ${item.border} shadow-md hover:shadow-xl transition-all`}
              >
                <div className={`w-14 h-14 ${item.bg} rounded-xl flex items-center justify-center mb-4 border-2 ${item.border}`}>
                  <div className={`w-7 h-7 bg-gradient-to-br ${item.color} rounded-lg flex items-center justify-center`}>
                    <item.icon className="w-5 h-5 text-white" />
                  </div>
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-2">{item.title}</h3>
                <p className="text-slate-600 leading-relaxed">{item.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Solution Section - Meridian Style */}
      <section className="py-24 px-4 bg-white">
        <div className="container mx-auto max-w-6xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <Badge className="mb-4 px-5 py-2 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full">
              <CheckCircle2 className="w-4 h-4 mr-2" />
              The Solution
            </Badge>
            <h2 className="text-4xl md:text-5xl font-bold text-slate-900 mb-4 leading-tight">
              Autonomous AI Agents That Work 24/7
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto leading-relaxed">
              A multi-agent AI system powered by OpenAi agent SDK and MCP that reasons, plans,
              and collaborates like a real team — handling your entire business autonomously.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 gap-8 items-start">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="space-y-4"
            >
              {[
                { icon: MessageSquare, title: "Sales Agent", desc: "Handles WhatsApp chats, orders, and payments automatically", color: "from-[#174143] to-[#427A76]", bg: "bg-teal-50", border: "border-teal-200" },
                { icon: Package, title: "Inventory Agent", desc: "Monitors stock and auto-notifies suppliers when low", color: "from-orange-600 to-orange-700", bg: "bg-orange-50", border: "border-orange-200" },
                { icon: TrendingUp, title: "Analytics Agent", desc: "Generates weekly summaries and demand predictions", color: "from-purple-600 to-indigo-600", bg: "bg-purple-50", border: "border-purple-200" },
                { icon: Globe, title: "Marketing Agent", desc: "Creates social posts and product descriptions with AI", color: "from-pink-600 to-rose-600", bg: "bg-pink-50", border: "border-pink-200" },
              ].map((agent, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1 }}
                  whileHover={{ y: -4 }}
                  className={`flex gap-4 items-start p-5 rounded-2xl border-2 ${agent.border} ${agent.bg} hover:shadow-lg transition-all cursor-pointer`}
                >
                  <div className={`w-12 h-12 bg-gradient-to-br ${agent.color} rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm`}>
                    <agent.icon className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-slate-900 mb-1">{agent.title}</h3>
                    <p className="text-sm text-slate-600 leading-relaxed">{agent.desc}</p>
                  </div>
                </motion.div>
              ))}
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="relative"
            >
              <div className="aspect-square bg-gradient-to-br from-slate-50 to-slate-100 rounded-3xl border-2 border-slate-200 flex items-center justify-center p-8 shadow-sm">
                <div className="text-center">
                  <div className="text-7xl mb-6">🤖</div>
                  <p className="text-slate-700 font-semibold text-lg">AI Agents Workflow</p>
                  <p className="text-slate-500 text-sm mt-2">Powered by LangGraph & MCP</p>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Stats Section - Meridian Style */}
      <section className="py-20 px-4 bg-slate-50">
        <div className="container mx-auto max-w-6xl">
          <div className="grid md:grid-cols-4 gap-6">
            {[
              { value: "1000+", label: "Active Businesses", icon: Users, color: "from-[#174143] to-[#427A76]", bg: "bg-teal-50", border: "border-teal-200" },
              { value: "50K+", label: "Orders Processed", icon: BarChart3, color: "from-purple-600 to-indigo-600", bg: "bg-purple-50", border: "border-purple-200" },
              { value: "99.9%", label: "Uptime", icon: Zap, color: "from-green-600 to-emerald-600", bg: "bg-green-50", border: "border-green-200" },
              { value: "24/7", label: "AI Support", icon: Clock, color: "from-orange-600 to-orange-700", bg: "bg-orange-50", border: "border-orange-200" },
            ].map((stat, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                whileHover={{ y: -4 }}
                className={`text-center p-8 rounded-2xl border-2 ${stat.border} ${stat.bg} hover:shadow-lg transition-all bg-white`}
              >
                <div className={`w-14 h-14 bg-gradient-to-br ${stat.color} rounded-xl flex items-center justify-center mx-auto mb-4 shadow-sm`}>
                  <stat.icon className="w-7 h-7 text-white" />
                </div>
                <div className="text-4xl font-bold mb-2 text-slate-900">{stat.value}</div>
                <div className="text-slate-600 text-sm font-medium">{stat.label}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works - Meridian Style with GSAP */}
      <section className="py-24 px-4 bg-white">
        <div className="container mx-auto max-w-6xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl md:text-5xl font-bold text-slate-900 mb-4 leading-tight">
              How It Works
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto leading-relaxed">
              Our multi-agent system uses LangGraph and MCP for autonomous decision-making
            </p>
          </motion.div>

          <MeridianCards
            cards={[
              { title: "Customer Orders", desc: "Customer sends WhatsApp message", icon: MessageSquare, color: "from-[#174143] to-[#427A76]", bg: "bg-teal-50", border: "border-teal-200" },
              { title: "AI Processes", desc: "Sales Agent confirms order & payment", icon: Zap, color: "from-purple-600 to-indigo-600", bg: "bg-purple-50", border: "border-purple-200" },
              { title: "Auto Updates", desc: "Inventory updates automatically", icon: Package, color: "from-orange-600 to-orange-700", bg: "bg-orange-50", border: "border-orange-200" },
              { title: "Analytics", desc: "Weekly reports generated", icon: TrendingUp, color: "from-green-600 to-emerald-600", bg: "bg-green-50", border: "border-green-200" },
            ]}
            columns={4}
          />
        </div>
      </section>

      {/* Features Grid - Meridian Style with GSAP Animation */}
      <section className="py-24 px-4 bg-slate-50">
        <div className="container mx-auto max-w-6xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl md:text-5xl font-bold text-slate-900 mb-4 leading-tight">
              Built for Pakistan&apos;s Digital Economy
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto leading-relaxed">
              Everything you need to run your business autonomously
            </p>
          </motion.div>

          <MeridianCards
            cards={[
              { icon: Shield, title: "Offline Mode", desc: "Works with limited connectivity, caches orders locally", color: "from-blue-600 to-cyan-600", bg: "bg-blue-50", border: "border-blue-200" },
              { icon: Globe, title: "Urdu Support", desc: "Full Urdu/English support for summaries and communication", color: "from-purple-600 to-indigo-600", bg: "bg-purple-50", border: "border-purple-200" },
              { icon: Zap, title: "Real-time Sync", desc: "Instant updates across all agents via MCP server", color: "from-[#174143] to-[#427A76]", bg: "bg-teal-50", border: "border-teal-200" },
              { icon: DollarSign, title: "Payment Tracking", desc: "Easypaisa, JazzCash, and cash payment monitoring", color: "from-green-600 to-emerald-600", bg: "bg-green-50", border: "border-green-200" },
              { icon: BarChart3, title: "Smart Analytics", desc: "Demand prediction and pricing recommendations", color: "from-orange-600 to-orange-700", bg: "bg-orange-50", border: "border-orange-200" },
              { icon: Star, title: "Auto Marketing", desc: "AI-generated social posts and product descriptions", color: "from-pink-600 to-rose-600", bg: "bg-pink-50", border: "border-pink-200" },
            ]}
            columns={3}
          />
        </div>
      </section>

      {/* CTA Section - Meridian Style */}
      <section className="py-24 px-4 bg-white">
        <div className="container mx-auto max-w-4xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="bg-gradient-to-br from-slate-50 to-slate-100 rounded-3xl border-2 border-slate-200 p-12 md:p-16 text-center shadow-sm"
          >
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4 leading-tight">
              Ready to Automate Your Business?
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto mb-8 leading-relaxed">
              Join thousands of Pakistani businesses already using BazaarFlow
            </p>
            <div className="flex flex-wrap gap-4 justify-center">
              <motion.div whileHover={{ y: -2 }} whileTap={{ scale: 0.98 }}>
                <Button asChild size="lg" className="h-12 px-8 text-base font-medium bg-gradient-to-r from-[#174143] to-[#427A76] hover:from-[#427A76] hover:to-[#174143] text-white rounded-xl shadow-md hover:shadow-lg transition-all">
                  <Link href="/dashboard">
                    Start Free Trial
                    <ArrowRight className="ml-2 w-5 h-5" />
                  </Link>
                </Button>
              </motion.div>
              <motion.div whileHover={{ y: -2 }} whileTap={{ scale: 0.98 }}>
                <Button asChild size="lg" variant="outline" className="h-12 px-8 text-base font-medium border-2 border-slate-300 text-slate-700 hover:bg-slate-100 rounded-xl transition-all">
                  <Link href="/contact">Contact Sales</Link>
                </Button>
              </motion.div>
            </div>
          </motion.div>
        </div>
      </section>
    </main>
  );
}

