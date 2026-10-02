"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Play, RotateCcw, CheckCircle2, Clock, TrendingUp, Package, DollarSign } from "lucide-react";

const demoSteps = [
  { agent: "Customer", message: "Received order from WhatsApp: '2x iPhone Charger'", type: "info" },
  { agent: "SalesAgent", message: "Confirmed order, checking inventory...", type: "processing" },
  { agent: "InventoryAgent", message: "Stock available for SKU-123. Current: 15 units", type: "success" },
  { agent: "SalesAgent", message: "Order confirmed. Total: PKR 2,400", type: "success" },
  { agent: "FinanceAgent", message: "Payment pending verification", type: "warning" },
  { agent: "FinanceAgent", message: "Payment verified. Receipt generated.", type: "success" },
  { agent: "InventoryAgent", message: "Stock updated. New count: 13 units", type: "info" },
  { agent: "InventoryAgent", message: "Stock below threshold. Reorder recommended.", type: "warning" },
  { agent: "AnalyticsAgent", message: "Demand predicted +12% next week", type: "info" },
  { agent: "AnalyticsAgent", message: "Suggested reorder quantity: 20 units", type: "success" },
];

export default function DemoPage() {
  const [logs, setLogs] = useState<typeof demoSteps>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [stats, setStats] = useState({
    orders: 0,
    revenue: 0,
    reorders: 0,
  });

  const runNextStep = () => {
    if (currentStep < demoSteps.length) {
      setLogs((prev) => [...prev, demoSteps[currentStep]]);
      setCurrentStep((prev) => prev + 1);

      // Update stats
      if (demoSteps[currentStep].agent === "SalesAgent" && demoSteps[currentStep].message.includes("confirmed")) {
        setStats((prev) => ({ ...prev, orders: prev.orders + 1, revenue: prev.revenue + 2400 }));
      }
      if (demoSteps[currentStep].agent === "InventoryAgent" && demoSteps[currentStep].message.includes("Reorder")) {
        setStats((prev) => ({ ...prev, reorders: prev.reorders + 1 }));
      }
    }
  };

  const runFullDemo = async () => {
    setIsRunning(true);
    setLogs([]);
    setCurrentStep(0);
    setStats({ orders: 0, revenue: 0, reorders: 0 });

    for (let i = 0; i < demoSteps.length; i++) {
      await new Promise((resolve) => setTimeout(resolve, 800));
      setLogs((prev) => [...prev, demoSteps[i]]);
      setCurrentStep(i + 1);

      if (demoSteps[i].agent === "SalesAgent" && demoSteps[i].message.includes("confirmed")) {
        setStats((prev) => ({ ...prev, orders: prev.orders + 1, revenue: prev.revenue + 2400 }));
      }
      if (demoSteps[i].agent === "InventoryAgent" && demoSteps[i].message.includes("Reorder")) {
        setStats((prev) => ({ ...prev, reorders: prev.reorders + 1 }));
      }
    }
    setIsRunning(false);
  };

  const reset = () => {
    setLogs([]);
    setCurrentStep(0);
    setStats({ orders: 0, revenue: 0, reorders: 0 });
    setIsRunning(false);
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case "success": return "text-green-600";
      case "warning": return "text-orange-600";
      case "processing": return "text-blue-600";
      default: return "text-slate-600";
    }
  };

  const getAgentColor = (agent: string) => {
    switch (agent) {
      case "SalesAgent": return "bg-teal-50 text-teal-700 border-teal-200";
      case "InventoryAgent": return "bg-orange-50 text-orange-700 border-orange-200";
      case "AnalyticsAgent": return "bg-purple-50 text-purple-700 border-purple-200";
      case "FinanceAgent": return "bg-green-50 text-green-700 border-green-200";
      default: return "bg-slate-50 text-slate-700 border-slate-200";
    }
  };

  return (
    <div className="min-h-screen py-20 px-4 bg-white">
      <div className="container mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="max-w-5xl mx-auto"
        >
          <div className="text-center mb-12">
            <Badge className="mb-4 px-5 py-2 bg-teal-50 text-teal-700 border border-teal-200 rounded-full">Interactive Demo</Badge>
            <h1 className="text-4xl md:text-5xl font-bold mb-4 text-slate-900 leading-tight">Live Demo Workflow</h1>
            <p className="text-lg text-slate-600 leading-relaxed">
              Watch how our AI agents collaborate to handle an end-to-end order
            </p>
          </div>

          {/* Stats Cards - Meridian Style */}
          <div className="grid md:grid-cols-3 gap-6 mb-8">
            <Card className="border-2 border-green-200 bg-green-50 shadow-sm rounded-2xl">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-green-700 mb-1 font-medium">Orders Processed</p>
                    <p className="text-3xl font-bold text-slate-900">{stats.orders}</p>
                  </div>
                  <div className="w-12 h-12 bg-gradient-to-br from-green-600 to-emerald-600 rounded-xl flex items-center justify-center shadow-sm">
                    <CheckCircle2 className="w-6 h-6 text-white" />
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="border-2 border-blue-200 bg-blue-50 shadow-sm rounded-2xl">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-blue-700 mb-1 font-medium">Revenue</p>
                    <p className="text-3xl font-bold text-slate-900">PKR {stats.revenue.toLocaleString()}</p>
                  </div>
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-cyan-600 rounded-xl flex items-center justify-center shadow-sm">
                    <DollarSign className="w-6 h-6 text-white" />
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="border-2 border-purple-200 bg-purple-50 shadow-sm rounded-2xl">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-purple-700 mb-1 font-medium">Pending Reorders</p>
                    <p className="text-3xl font-bold text-slate-900">{stats.reorders}</p>
                  </div>
                  <div className="w-12 h-12 bg-gradient-to-br from-purple-600 to-indigo-600 rounded-xl flex items-center justify-center shadow-sm">
                    <Package className="w-6 h-6 text-white" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Main Demo Area */}
          <div className="grid lg:grid-cols-3 gap-6">
            {/* Agent Trace */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Agent Trace</CardTitle>
                    <CardDescription>Real-time agent communication log</CardDescription>
                  </div>
                  <Badge variant="outline" className={isRunning ? "animate-pulse" : ""}>
                    {isRunning ? (
                      <>
                        <Clock className="w-3 h-3 mr-1" />
                        Running
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="w-3 h-3 mr-1" />
                        Ready
                      </>
                    )}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="h-96 overflow-auto rounded-lg border bg-slate-50 dark:bg-slate-900 p-4 font-mono text-sm space-y-2 mb-4">
                  <AnimatePresence>
                    {logs.map((log, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.3 }}
                        className="flex items-start gap-2"
                      >
                        <Badge className={`${getAgentColor(log.agent)} text-xs flex-shrink-0`}>
                          {log.agent}
                        </Badge>
                        <span className={getTypeColor(log.type)}>{log.message}</span>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                  {logs.length === 0 && (
                    <p className="text-muted-foreground text-center py-20">
                      Click &quot;Run Full Demo&quot; to start the simulation
                    </p>
                  )}
                </div>

                <div className="flex gap-3">
                  <Button
                    onClick={runFullDemo}
                    disabled={isRunning}
                    className="flex-1"
                  >
                    <Play className="w-4 h-4 mr-2" />
                    Run Full Demo
                  </Button>
                  <Button
                    onClick={runNextStep}
                    disabled={isRunning || currentStep >= demoSteps.length}
                    variant="outline"
                  >
                    Step
                  </Button>
                  <Button onClick={reset} variant="outline">
                    <RotateCcw className="w-4 h-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Progress & Info */}
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Progress</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between text-sm mb-2">
                        <span>Steps Completed</span>
                        <span className="font-semibold">{currentStep}/{demoSteps.length}</span>
                      </div>
                      <div className="w-full bg-muted rounded-full h-2">
                        <motion.div
                          className="bg-primary h-2 rounded-full"
                          initial={{ width: 0 }}
                          animate={{ width: `${(currentStep / demoSteps.length) * 100}%` }}
                          transition={{ duration: 0.3 }}
                        />
                      </div>
                    </div>
                    <Separator />
                    <div className="space-y-2">
                      <h4 className="font-semibold text-sm">Active Agents</h4>
                      {["SalesAgent", "InventoryAgent", "FinanceAgent", "AnalyticsAgent"].map((agent) => (
                        <div key={agent} className="flex items-center justify-between text-sm">
                          <span className="text-muted-foreground">{agent}</span>
                          <div className={`w-2 h-2 rounded-full ${
                            logs.some((l) => l.agent === agent) ? "bg-green-500 animate-pulse" : "bg-gray-300"
                          }`} />
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="w-5 h-5" />
                    Insights
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20">
                    <p className="font-semibold text-green-700 dark:text-green-400">Order Success Rate</p>
                    <p className="text-2xl font-bold text-green-600">100%</p>
                  </div>
                  <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                    <p className="font-semibold text-blue-700 dark:text-blue-400">Avg Response Time</p>
                    <p className="text-2xl font-bold text-blue-600">1.2s</p>
                  </div>
                  <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/20">
                    <p className="font-semibold text-purple-700 dark:text-purple-400">Automation Level</p>
                    <p className="text-2xl font-bold text-purple-600">95%</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
