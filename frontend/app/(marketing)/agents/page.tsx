"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MessageSquare, Package, TrendingUp, ArrowRight, CheckCircle2, Sparkles, DollarSign, Megaphone } from "lucide-react";

const fadeInUp = {
  initial: { opacity: 0, y: 40 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true },
  transition: { duration: 0.6 }
};

export default function AgentsPage() {
  const agents = [
    {
      id: "sales",
      name: "Sales Agent",
      icon: MessageSquare,
      desc: "Handles chats, orders and payments via WhatsApp.",
      color: "from-[#174143] to-[#427A76]",
      bgColor: "bg-[#174143]/5",
      borderColor: "border-[#174143]/20",
      features: [
        "24/7 WhatsApp chat handling",
        "Order confirmation & tracking",
        "Payment verification",
        "Receipt generation",
        "Customer query resolution",
      ],
    },
    {
      id: "inventory",
      name: "Inventory Agent",
      icon: Package,
      desc: "Monitors stock and auto-notifies suppliers.",
      color: "from-orange-600 to-orange-700",
      bgColor: "bg-orange-50",
      borderColor: "border-orange-200",
      features: [
        "Real-time stock monitoring",
        "Automatic reorder alerts",
        "Supplier notifications",
        "Stock prediction",
        "Low inventory warnings",
      ],
    },
    {
      id: "analytics",
      name: "Analytics Agent",
      icon: TrendingUp,
      desc: "Generates summaries, demand predictions and pricing advice.",
      color: "from-purple-600 to-indigo-600",
      bgColor: "bg-purple-50",
      borderColor: "border-purple-200",
      features: [
        "Weekly Urdu/English summaries",
        "Demand forecasting",
        "Pricing recommendations",
        "Sales trend analysis",
        "Financial reconciliation",
      ],
    },
    {
      id: "finance",
      name: "Finance Agent",
      icon: DollarSign,
      desc: "Tracks payments and reconciles transactions automatically.",
      color: "from-green-600 to-emerald-600",
      bgColor: "bg-green-50",
      borderColor: "border-green-200",
      features: [
        "Easypaisa/JazzCash tracking",
        "RAAST payment monitoring",
        "Automatic reconciliation",
        "Revenue analytics",
        "Payment reminders",
      ],
    },
    {
      id: "marketing",
      name: "Marketing Agent",
      icon: Megaphone,
      desc: "Creates social media content and product descriptions with AI.",
      color: "from-pink-600 to-rose-600",
      bgColor: "bg-pink-50",
      borderColor: "border-pink-200",
      features: [
        "AI-generated social posts",
        "Product descriptions",
        "Facebook/Instagram content",
        "WhatsApp broadcasts",
        "Promotional campaigns",
      ],
    },
  ];

  return (
    <div className="min-h-screen bg-white">
      {/* Hero Section - 3D Enhanced */}
      <section className="py-32 px-4 relative overflow-hidden">
        {/* 3D Background */}
        <div className="absolute inset-0 bg-gradient-to-br from-gray-50 via-white to-blue-50/30" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808008_1px,transparent_1px),linear-gradient(to_bottom,#80808008_1px,transparent_1px)] bg-[size:40px_40px]" />

        <div className="container mx-auto relative z-10">
          <motion.div {...fadeInUp} className="max-w-3xl mx-auto text-center">
            <motion.div
              whileHover={{ scale: 1.05 }}
              className="inline-block mb-6"
            >
              <Badge className="px-5 py-2.5 bg-gradient-to-r from-[#174143] to-[#427A76] text-white border-0 shadow-lg shadow-[#174143]/20">
                <Sparkles className="w-3.5 h-3.5 mr-1.5" />
                AI-Powered Agents
              </Badge>
            </motion.div>
            <h1 className="text-6xl md:text-7xl font-bold mb-6 bg-gradient-to-br from-[#174143] via-[#427A76] to-[#174143] bg-clip-text text-transparent" style={{ textShadow: '0 4px 20px rgba(23, 65, 67, 0.1)' }}>
              Meet Your AI Team
            </h1>
            <p className="text-xl md:text-2xl text-slate-700 font-medium leading-relaxed">
              Five specialized agents working together to automate your entire business workflow
            </p>
          </motion.div>
        </div>
      </section>

      {/* Agents Grid - Meridian-Inspired */}
      <section className="py-20 px-4 bg-slate-50">
        <div className="container mx-auto max-w-7xl">
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-16">
            {agents.map((agent, i) => {
              return (
                <motion.div
                  key={agent.id}
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: i * 0.1 }}
                  whileHover={{ y: -8 }}
                  className="group"
                >
                  <Card className={`h-full border-2 ${agent.borderColor} ${agent.bgColor} hover:shadow-2xl transition-all duration-300 cursor-pointer overflow-hidden relative backdrop-blur-sm`}>
                    {/* Subtle gradient overlay on hover */}
                    <div className={`absolute inset-0 bg-gradient-to-br ${agent.color} opacity-0 group-hover:opacity-5 transition-opacity duration-300`} />

                    <CardHeader className="relative z-10 pb-4">
                      {/* Icon with gradient background */}
                      <motion.div
                        className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${agent.color} p-0.5 mb-4 shadow-md group-hover:shadow-xl transition-all`}
                        whileHover={{ scale: 1.05, rotate: 5 }}
                        transition={{ duration: 0.3 }}
                      >
                        <div className="w-full h-full bg-white rounded-2xl flex items-center justify-center">
                          <agent.icon className="w-8 h-8 text-slate-800" />
                        </div>
                      </motion.div>
                      <CardTitle className="text-xl mb-2 text-slate-900 group-hover:text-transparent group-hover:bg-gradient-to-r group-hover:bg-clip-text transition-all" style={{ backgroundImage: `linear-gradient(to right, var(--tw-gradient-stops))`, backgroundClip: 'text' }}>
                        {agent.name}
                      </CardTitle>
                      <CardDescription className="text-sm text-slate-600 leading-relaxed">{agent.desc}</CardDescription>
                    </CardHeader>
                    <CardContent className="relative z-10 pt-0">
                      <div className="space-y-2.5 mb-6">
                        {agent.features.map((feature, idx) => (
                          <motion.div
                            key={idx}
                            className="flex items-start gap-2.5"
                            initial={{ opacity: 0, x: -10 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            transition={{ delay: idx * 0.08 }}
                          >
                            <div className={`w-5 h-5 rounded-full bg-gradient-to-br ${agent.color} flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm`}>
                              <CheckCircle2 className="w-3 h-3 text-white" />
                            </div>
                            <span className="text-sm text-slate-700 leading-snug">{feature}</span>
                          </motion.div>
                        ))}
                      </div>
                      <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                        <Button asChild variant="outline" className={`w-full group/btn border-2 ${agent.borderColor} hover:bg-gradient-to-r ${agent.color} hover:text-white hover:border-transparent transition-all shadow-sm hover:shadow-md`}>
                          <Link href={`/chat/${agent.id}`}>
                            Chat with Agent
                            <ArrowRight className="ml-2 w-4 h-4 group-hover/btn:translate-x-1 transition-transform" />
                          </Link>
                        </Button>
                      </motion.div>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </div>

          {/* Detailed View with Tabs */}
          <motion.div {...fadeInUp}>
            <Card className="border-2">
              <CardHeader>
                <CardTitle className="text-3xl">How They Work Together</CardTitle>
                <CardDescription>
                  See how our agents collaborate to handle your business operations seamlessly
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="sales" className="w-full">
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="sales">Sales</TabsTrigger>
                    <TabsTrigger value="inventory">Inventory</TabsTrigger>
                    <TabsTrigger value="analytics">Analytics</TabsTrigger>
                  </TabsList>
                  <TabsContent value="sales" className="mt-6 space-y-4">
                    <h3 className="text-xl font-semibold">Sales Agent Workflow</h3>
                    <p className="text-muted-foreground">
                      The Sales Agent is your 24/7 customer service representative, handling all WhatsApp interactions with customers.
                    </p>
                    <div className="bg-muted/50 p-6 rounded-lg space-y-3">
                      <p className="font-mono text-sm">1. Customer sends: &ldquo;I want 2 iPhone chargers&rdquo;</p>
                      <p className="font-mono text-sm">2. Agent checks inventory availability</p>
                      <p className="font-mono text-sm">3. Confirms order and price: &ldquo;PKR 2,400&rdquo;</p>
                      <p className="font-mono text-sm">4. Sends payment instructions</p>
                      <p className="font-mono text-sm">5. Generates digital receipt</p>
                    </div>
                  </TabsContent>
                  <TabsContent value="inventory" className="mt-6 space-y-4">
                    <h3 className="text-xl font-semibold">Inventory Agent Workflow</h3>
                    <p className="text-muted-foreground">
                      The Inventory Agent monitors your stock levels and ensures you never run out of popular items.
                    </p>
                    <div className="bg-muted/50 p-6 rounded-lg space-y-3">
                      <p className="font-mono text-sm">1. Monitors stock levels in real-time</p>
                      <p className="font-mono text-sm">2. Detects low inventory (below threshold)</p>
                      <p className="font-mono text-sm">3. Predicts reorder quantity based on demand</p>
                      <p className="font-mono text-sm">4. Sends notification to supplier</p>
                      <p className="font-mono text-sm">5. Updates stock when shipment arrives</p>
                    </div>
                  </TabsContent>
                  <TabsContent value="analytics" className="mt-6 space-y-4">
                    <h3 className="text-xl font-semibold">Analytics Agent Workflow</h3>
                    <p className="text-muted-foreground">
                      The Analytics Agent provides insights and recommendations to help you grow your business.
                    </p>
                    <div className="bg-muted/50 p-6 rounded-lg space-y-3">
                      <p className="font-mono text-sm">1. Collects sales data throughout the week</p>
                      <p className="font-mono text-sm">2. Analyzes trends and patterns</p>
                      <p className="font-mono text-sm">3. Generates weekly summary (Urdu/English)</p>
                      <p className="font-mono text-sm">4. Predicts next week&rsquo;s demand</p>
                      <p className="font-mono text-sm">5. Suggests pricing optimizations</p>
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
