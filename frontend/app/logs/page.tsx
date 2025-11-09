"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  Activity, MessageSquare, Package, DollarSign, BarChart3, Megaphone,
  ArrowRight, CheckCircle2, AlertCircle, Clock, Zap, Database
} from "lucide-react";

interface LogEntry {
  id: string;
  timestamp: Date;
  agent: string;
  action: string;
  message: string;
  status: "success" | "pending" | "error";
  reasoning?: string;
  toolInvoked?: string;
}

export default function AgentLogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([
    {
      id: "1",
      timestamp: new Date(Date.now() - 5000),
      agent: "Sales Agent",
      action: "Customer Query",
      message: "Received order request for iPhone 15",
      status: "success",
      reasoning: "Customer wants to purchase iPhone 15. Checking inventory availability.",
      toolInvoked: "inventory_check",
    },
    {
      id: "2",
      timestamp: new Date(Date.now() - 4500),
      agent: "Inventory Agent",
      action: "Stock Check",
      message: "iPhone 15 stock: 5 units available",
      status: "success",
      reasoning: "Stock level is low (< 10 units). Triggering low stock alert.",
      toolInvoked: "get_stock_level",
    },
    {
      id: "3",
      timestamp: new Date(Date.now() - 4000),
      agent: "Inventory Agent",
      action: "Auto-Reorder",
      message: "Sent reorder notification to supplier",
      status: "success",
      reasoning: "Stock below threshold. Autonomous decision: Notify supplier for reorder.",
      toolInvoked: "notify_supplier",
    },
    {
      id: "4",
      timestamp: new Date(Date.now() - 3500),
      agent: "Sales Agent",
      action: "Order Creation",
      message: "Created order #1245 for PKR 285,000",
      status: "success",
      reasoning: "Stock available. Creating order and requesting payment.",
      toolInvoked: "create_order",
    },
    {
      id: "5",
      timestamp: new Date(Date.now() - 3000),
      agent: "Finance Agent",
      action: "Payment Request",
      message: "Awaiting Easypaisa payment confirmation",
      status: "pending",
      reasoning: "Payment initiated. Monitoring RAAST API for confirmation.",
      toolInvoked: "raast_payment_check",
    },
    {
      id: "6",
      timestamp: new Date(Date.now() - 2500),
      agent: "Finance Agent",
      action: "Payment Confirmed",
      message: "Payment received: PKR 285,000 via Easypaisa",
      status: "success",
      reasoning: "Payment verified. Notifying Sales Agent to proceed with delivery.",
      toolInvoked: "verify_payment",
    },
    {
      id: "7",
      timestamp: new Date(Date.now() - 2000),
      agent: "Inventory Agent",
      action: "Stock Update",
      message: "Updated iPhone 15 stock: 4 units remaining",
      status: "success",
      reasoning: "Order fulfilled. Updating inventory. Stock critically low.",
      toolInvoked: "update_stock",
    },
    {
      id: "8",
      timestamp: new Date(Date.now() - 1500),
      agent: "Analytics Agent",
      action: "Demand Prediction",
      message: "Predicted +25% demand for iPhone 15 (Eid season)",
      status: "success",
      reasoning: "Historical data shows increased demand during Eid. Recommending stock increase.",
      toolInvoked: "predict_demand",
    },
    {
      id: "9",
      timestamp: new Date(Date.now() - 1000),
      agent: "Marketing Agent",
      action: "Content Generation",
      message: "Generated Facebook post for iPhone 15 promotion",
      status: "success",
      reasoning: "Low stock + high demand = opportunity for promotion. Creating social media content.",
      toolInvoked: "generate_social_post",
    },
    {
      id: "10",
      timestamp: new Date(Date.now() - 500),
      agent: "MCP Server",
      action: "Inter-Agent Communication",
      message: "All agents synchronized. Workflow complete.",
      status: "success",
      reasoning: "Multi-agent collaboration successful. Order processed end-to-end.",
      toolInvoked: "mcp_sync",
    },
  ]);

  const [filter, setFilter] = useState<string>("all");
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      // Simulate new log entry
      const agents = ["Sales Agent", "Inventory Agent", "Finance Agent", "Analytics Agent", "Marketing Agent"];
      const actions = ["Query Processed", "Stock Updated", "Payment Verified", "Report Generated", "Content Created"];
      const randomAgent = agents[Math.floor(Math.random() * agents.length)];
      const randomAction = actions[Math.floor(Math.random() * actions.length)];

      const newLog: LogEntry = {
        id: Date.now().toString(),
        timestamp: new Date(),
        agent: randomAgent,
        action: randomAction,
        message: `${randomAction} successfully`,
        status: "success",
        reasoning: "Autonomous agent decision based on current context.",
        toolInvoked: "mcp_tool_" + Math.floor(Math.random() * 100),
      };

      setLogs((prev) => [newLog, ...prev].slice(0, 50)); // Keep last 50 logs
    }, 5000);

    return () => clearInterval(interval);
  }, [autoRefresh]);

  const filteredLogs = filter === "all" ? logs : logs.filter((log) => log.agent.toLowerCase().includes(filter));

  const agentColors: Record<string, string> = {
    "Sales Agent": "text-[#174143] bg-[#174143]/10",
    "Inventory Agent": "text-orange-600 bg-orange-100",
    "Finance Agent": "text-green-600 bg-green-100",
    "Analytics Agent": "text-purple-600 bg-purple-100",
    "Marketing Agent": "text-pink-600 bg-pink-100",
    "MCP Server": "text-blue-600 bg-blue-100",
  };

  const agentIcons: Record<string, any> = {
    "Sales Agent": MessageSquare,
    "Inventory Agent": Package,
    "Finance Agent": DollarSign,
    "Analytics Agent": BarChart3,
    "Marketing Agent": Megaphone,
    "MCP Server": Database,
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30 py-8 px-4">
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <Badge className="mb-4 px-5 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white border-0">
            <Activity className="w-4 h-4 mr-2" />
            Real-Time Monitoring
          </Badge>
          <h1 className="text-4xl font-bold mb-2 text-slate-900">Agent Interaction Logs</h1>
          <p className="text-slate-600">MCP Server Communication & Multi-Agent Reasoning</p>
        </motion.div>

        {/* Controls */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-6 flex flex-wrap gap-3 justify-center"
        >
          <Button
            variant={filter === "all" ? "default" : "outline"}
            onClick={() => setFilter("all")}
            className={filter === "all" ? "bg-[#174143]" : ""}
          >
            All Agents
          </Button>
          <Button
            variant={filter === "sales" ? "default" : "outline"}
            onClick={() => setFilter("sales")}
            className={filter === "sales" ? "bg-[#174143]" : ""}
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            Sales
          </Button>
          <Button
            variant={filter === "inventory" ? "default" : "outline"}
            onClick={() => setFilter("inventory")}
            className={filter === "inventory" ? "bg-orange-600" : ""}
          >
            <Package className="w-4 h-4 mr-2" />
            Inventory
          </Button>
          <Button
            variant={filter === "finance" ? "default" : "outline"}
            onClick={() => setFilter("finance")}
            className={filter === "finance" ? "bg-green-600" : ""}
          >
            <DollarSign className="w-4 h-4 mr-2" />
            Finance
          </Button>
          <Button
            variant={filter === "analytics" ? "default" : "outline"}
            onClick={() => setFilter("analytics")}
            className={filter === "analytics" ? "bg-purple-600" : ""}
          >
            <BarChart3 className="w-4 h-4 mr-2" />
            Analytics
          </Button>
          <Button
            variant={filter === "marketing" ? "default" : "outline"}
            onClick={() => setFilter("marketing")}
            className={filter === "marketing" ? "bg-pink-600" : ""}
          >
            <Megaphone className="w-4 h-4 mr-2" />
            Marketing
          </Button>
          <Button
            variant="outline"
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={autoRefresh ? "border-green-500 text-green-600" : ""}
          >
            {autoRefresh ? "🟢 Live" : "⏸️ Paused"}
          </Button>
        </motion.div>

        {/* Logs Timeline */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="space-y-4"
        >
          <AnimatePresence>
            {filteredLogs.map((log, index) => {
              const Icon = agentIcons[log.agent] || Activity;
              const colorClass = agentColors[log.agent] || "text-slate-600 bg-slate-100";

              return (
                <motion.div
                  key={log.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <Card className="border-l-4 border-l-blue-500 hover:shadow-lg transition-shadow">
                    <CardContent className="p-6">
                      <div className="flex items-start gap-4">
                        {/* Icon */}
                        <div className={`w-12 h-12 rounded-full ${colorClass} flex items-center justify-center flex-shrink-0`}>
                          <Icon className="w-6 h-6" />
                        </div>

                        {/* Content */}
                        <div className="flex-1">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-3">
                              <Badge className={colorClass}>{log.agent}</Badge>
                              <span className="text-sm font-semibold text-slate-900">{log.action}</span>
                            </div>
                            <div className="flex items-center gap-2 text-xs text-slate-500">
                              <Clock className="w-3 h-3" />
                              {log.timestamp.toLocaleTimeString()}
                            </div>
                          </div>

                          <p className="text-slate-700 mb-3">{log.message}</p>

                          {log.reasoning && (
                            <div className="bg-indigo-50 rounded-lg p-3 mb-3 border border-indigo-200">
                              <div className="flex items-start gap-2">
                                <Zap className="w-4 h-4 text-indigo-600 mt-0.5 flex-shrink-0" />
                                <div>
                                  <p className="text-xs font-semibold text-indigo-900 mb-1">AI Reasoning:</p>
                                  <p className="text-xs text-indigo-700">{log.reasoning}</p>
                                </div>
                              </div>
                            </div>
                          )}

                          <div className="flex items-center justify-between">
                            {log.toolInvoked && (
                              <Badge variant="outline" className="text-xs">
                                <Database className="w-3 h-3 mr-1" />
                                Tool: {log.toolInvoked}
                              </Badge>
                            )}
                            <div className="flex items-center gap-2">
                              {log.status === "success" && (
                                <Badge className="bg-green-100 text-green-700 border-green-200">
                                  <CheckCircle2 className="w-3 h-3 mr-1" />
                                  Success
                                </Badge>
                              )}
                              {log.status === "pending" && (
                                <Badge className="bg-blue-100 text-blue-700 border-blue-200">
                                  <Clock className="w-3 h-3 mr-1" />
                                  Pending
                                </Badge>
                              )}
                              {log.status === "error" && (
                                <Badge className="bg-red-100 text-red-700 border-red-200">
                                  <AlertCircle className="w-3 h-3 mr-1" />
                                  Error
                                </Badge>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </motion.div>

        {filteredLogs.length === 0 && (
          <div className="text-center py-12">
            <Activity className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-500">No logs found for this filter</p>
          </div>
        )}
      </div>
    </div>
  );
}

