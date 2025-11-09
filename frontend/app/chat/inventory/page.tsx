"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Package, Send, Bot, User, Loader2, AlertTriangle, TrendingUp, BarChart3 } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "agent";
  content: string;
  timestamp: Date;
  type?: "alert" | "info" | "success";
}

export default function InventoryAgentChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "agent",
      content: "📦 Hello! I'm your Inventory Agent. I monitor stock levels, predict shortages, and auto-notify suppliers. Ask me about stock status, reorder alerts, or inventory predictions!",
      timestamp: new Date(),
      type: "info",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const userInput = input;
    setInput("");
    setLoading(true);

    // Simulate inventory agent responses
    setTimeout(() => {
      let response = "";
      let type: "alert" | "info" | "success" = "info";

      if (userInput.toLowerCase().includes("stock") || userInput.toLowerCase().includes("inventory")) {
        response = "📊 Current Stock Status:\n\n• iPhone 15: 5 units (⚠️ Low Stock)\n• MacBook Pro: 12 units (✅ Good)\n• iPad Pro: 3 units (🔴 Critical)\n• Apple Watch: 8 units (✅ Good)\n\nRecommendation: Reorder iPhone 15 and iPad Pro immediately!";
        type = "alert";
      } else if (userInput.toLowerCase().includes("reorder") || userInput.toLowerCase().includes("supplier")) {
        response = "🔔 Auto-Reorder Alert Sent!\n\nSupplier: Tech Distributors Karachi\nProducts:\n• iPhone 15 - 20 units\n• iPad Pro - 15 units\n\nExpected Delivery: 2-3 business days\nTotal Cost: PKR 2,450,000";
        type = "success";
      } else if (userInput.toLowerCase().includes("predict") || userInput.toLowerCase().includes("forecast")) {
        response = "📈 Demand Prediction (Next 7 Days):\n\n• iPhone 15: +25% demand (Eid season)\n• MacBook Pro: +10% demand\n• iPad Pro: +30% demand (Back to school)\n\nSuggested Action: Increase stock by 40% for high-demand items";
        type = "info";
      } else if (userInput.toLowerCase().includes("low") || userInput.toLowerCase().includes("alert")) {
        response = "⚠️ Low Stock Alerts:\n\n1. iPad Pro - Only 3 units left\n2. iPhone 15 - Only 5 units left\n\nAuto-notification sent to supplier 2 hours ago. Awaiting confirmation.";
        type = "alert";
      } else {
        response = "I can help you with:\n• Check stock levels\n• Reorder products\n• Predict demand\n• View low stock alerts\n\nWhat would you like to know?";
        type = "info";
      }

      const agentMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        content: response,
        timestamp: new Date(),
        type,
      };

      setMessages((prev) => [...prev, agentMessage]);
      setLoading(false);
    }, 1500);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const quickActions = [
    { icon: Package, label: "Stock Status", message: "Show current stock levels" },
    { icon: AlertTriangle, label: "Low Stock", message: "Show low stock alerts" },
    { icon: TrendingUp, label: "Predictions", message: "Predict demand for next week" },
    { icon: BarChart3, label: "Reorder", message: "Trigger auto-reorder" },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-orange-50/30 py-8 px-4">
      <div className="container mx-auto max-w-5xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-6"
        >
          <Badge className="mb-4 px-5 py-2 bg-gradient-to-r from-orange-600 to-orange-700 text-white border-0">
            <Package className="w-4 h-4 mr-2" />
            Live AI Agent
          </Badge>
          <h1 className="text-4xl font-bold mb-2 text-orange-900">Inventory Agent Chat</h1>
          <p className="text-orange-700">Real-time stock monitoring and predictions</p>
        </motion.div>

        {/* Chat Container */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
        >
          <Card className="border-2 border-orange-200 shadow-2xl">
            <CardHeader className="bg-gradient-to-r from-orange-600 to-orange-700 text-white">
              <CardTitle className="flex items-center gap-2">
                <Package className="w-5 h-5" />
                Inventory Agent - Monitoring
                <span className="ml-auto flex items-center gap-2">
                  <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                  <span className="text-sm font-normal">Active</span>
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {/* Messages Area */}
              <div className="h-[500px] overflow-y-auto p-6 space-y-4 bg-white">
                <AnimatePresence>
                  {messages.map((message) => (
                    <motion.div
                      key={message.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={`flex gap-3 max-w-[80%] ${
                          message.role === "user" ? "flex-row-reverse" : "flex-row"
                        }`}
                      >
                        {/* Avatar */}
                        <div
                          className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                            message.role === "user"
                              ? "bg-orange-600 text-white"
                              : "bg-gradient-to-br from-orange-500 to-orange-700 text-white"
                          }`}
                        >
                          {message.role === "user" ? <User className="w-5 h-5" /> : <Package className="w-5 h-5" />}
                        </div>

                        {/* Message Bubble */}
                        <div
                          className={`rounded-2xl px-4 py-3 ${
                            message.role === "user"
                              ? "bg-orange-600 text-white"
                              : message.type === "alert"
                              ? "bg-red-50 text-red-900 border-2 border-red-200"
                              : message.type === "success"
                              ? "bg-green-50 text-green-900 border-2 border-green-200"
                              : "bg-slate-100 text-slate-900 border border-slate-200"
                          }`}
                        >
                          <p className="text-sm leading-relaxed whitespace-pre-line">{message.content}</p>
                          <p
                            className={`text-xs mt-1 ${
                              message.role === "user" ? "text-white/70" : "text-slate-500"
                            }`}
                          >
                            {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                          </p>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>

                {loading && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex justify-start"
                  >
                    <div className="flex gap-3 max-w-[80%]">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-orange-500 to-orange-700 flex items-center justify-center">
                        <Package className="w-5 h-5 text-white" />
                      </div>
                      <div className="bg-slate-100 rounded-2xl px-4 py-3 border border-slate-200">
                        <div className="flex gap-1">
                          <span className="w-2 h-2 bg-orange-600 rounded-full animate-bounce"></span>
                          <span className="w-2 h-2 bg-orange-600 rounded-full animate-bounce delay-100"></span>
                          <span className="w-2 h-2 bg-orange-600 rounded-full animate-bounce delay-200"></span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Quick Actions */}
              <div className="border-t border-slate-200 p-4 bg-orange-50/50">
                <p className="text-xs text-slate-600 mb-2">Quick Actions:</p>
                <div className="flex flex-wrap gap-2">
                  {quickActions.map((action, i) => (
                    <Button
                      key={i}
                      variant="outline"
                      size="sm"
                      onClick={() => setInput(action.message)}
                      className="text-xs border-orange-300 hover:bg-orange-100"
                    >
                      <action.icon className="w-3 h-3 mr-1" />
                      {action.label}
                    </Button>
                  ))}
                </div>
              </div>

              {/* Input Area */}
              <div className="border-t border-slate-200 p-6 bg-white">
                <div className="flex gap-3">
                  <Input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask about inventory..."
                    disabled={loading}
                    className="flex-1 h-12 border-2 border-orange-300 focus:border-orange-600 focus:ring-2 focus:ring-orange-600/20 rounded-xl text-base"
                  />
                  <Button
                    onClick={handleSend}
                    disabled={loading || !input.trim()}
                    className="h-12 px-6 bg-gradient-to-r from-orange-600 to-orange-700 hover:from-orange-700 hover:to-orange-600 text-white rounded-xl shadow-lg"
                  >
                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}

