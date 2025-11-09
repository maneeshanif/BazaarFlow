"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Target, Users, Zap, Globe, Heart, TrendingUp } from "lucide-react";

const fadeInUp = {
  initial: { opacity: 0, y: 40 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true },
  transition: { duration: 0.6 }
};

export default function AboutPage() {
  return (
  <div className="min-h-screen bg-white">
      {/* Hero Section - Meridian Style */}
      <section className="py-20 px-4 bg-slate-50">
        <div className="container mx-auto">
          <motion.div {...fadeInUp} className="max-w-3xl mx-auto text-center">
            <Badge className="mb-6 px-5 py-2 bg-teal-50 text-teal-700 border border-teal-200 rounded-full">About Us</Badge>
            <h1 className="text-4xl md:text-5xl font-bold mb-4 text-slate-900 leading-tight">About BazaarFlow</h1>
            <p className="text-lg text-slate-600 leading-relaxed">
              Agentic AI Platform built for Pakistan&apos;s informal digital economy.
              Created for the National Agentic AI Hackathon Finale.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Mission Section - Meridian Style */}
      <section className="py-20 px-4 bg-white">
        <div className="container mx-auto max-w-6xl">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <motion.div {...fadeInUp}>
              <h2 className="text-3xl md:text-4xl font-bold mb-6 text-slate-900 leading-tight">Our Mission</h2>
              <p className="text-base text-slate-600 mb-6 leading-relaxed">
                Help micro-merchants accept orders, collect payments, and manage inventory
                with autonomous agents that work over channels they already use.
              </p>
              <p className="text-base text-slate-600 leading-relaxed">
                We believe that every small business in Pakistan deserves access to
                cutting-edge AI technology, regardless of their technical expertise or budget.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <Card className="border-2 border-slate-200 bg-slate-50 shadow-sm rounded-2xl">
                <CardContent className="p-8">
                  <div className="grid grid-cols-2 gap-6">
                    {[
                      { icon: Users, label: "Micro-Businesses", value: "1000+", color: "from-[#174143] to-[#427A76]", bg: "bg-teal-50" },
                      { icon: Zap, label: "AI Agents", value: "5", color: "from-purple-600 to-indigo-600", bg: "bg-purple-50" },
                      { icon: Globe, label: "Cities", value: "50+", color: "from-orange-600 to-orange-700", bg: "bg-orange-50" },
                      { icon: TrendingUp, label: "Growth", value: "200%", color: "from-green-600 to-emerald-600", bg: "bg-green-50" },
                    ].map((stat, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.4, delay: i * 0.1 }}
                        className="text-center"
                      >
                        <div className={`w-12 h-12 bg-gradient-to-br ${stat.color} rounded-xl flex items-center justify-center mx-auto mb-3 shadow-sm`}>
                          <stat.icon className="w-6 h-6 text-white" />
                        </div>
                        <p className="text-2xl font-bold mb-1 text-slate-900">{stat.value}</p>
                        <p className="text-xs text-slate-600">{stat.label}</p>
                      </motion.div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Values Section - Meridian Style */}
      <section className="py-20 px-4 bg-slate-50">
        <div className="container mx-auto max-w-6xl">
          <motion.div {...fadeInUp} className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold mb-4 text-slate-900 leading-tight">Our Values</h2>
            <p className="text-base text-slate-600 max-w-2xl mx-auto leading-relaxed">
              The principles that guide everything we do
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                icon: Target,
                title: "Accessibility First",
                desc: "Making AI accessible to every small business, regardless of technical knowledge.",
                color: "from-[#174143] to-[#427A76]",
                bg: "bg-teal-50",
                border: "border-teal-200"
              },
              {
                icon: Heart,
                title: "Community Focused",
                desc: "Building solutions that truly serve Pakistan's informal economy.",
                color: "from-pink-600 to-rose-600",
                bg: "bg-pink-50",
                border: "border-pink-200"
              },
              {
                icon: Zap,
                title: "Innovation Driven",
                desc: "Leveraging cutting-edge AI to solve real-world business challenges.",
                color: "from-purple-600 to-indigo-600",
                bg: "bg-purple-50",
                border: "border-purple-200"
              },
            ].map((value, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                whileHover={{ y: -4 }}
              >
                <Card className={`h-full border-2 ${value.border} bg-white hover:shadow-lg transition-all rounded-2xl`}>
                  <CardHeader className="pb-4">
                    <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${value.color} flex items-center justify-center mb-4 shadow-sm`}>
                      <value.icon className="w-6 h-6 text-white" />
                    </div>
                    <CardTitle className="text-lg font-semibold text-slate-900">{value.title}</CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <p className="text-sm text-slate-600 leading-relaxed">{value.desc}</p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
