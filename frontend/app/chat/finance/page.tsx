"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DollarSign, Send, Bot, User, Loader2, CreditCard, TrendingUp, Wallet } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "agent";
  content: string;
  timestamp: Date;
  type?: "payment" | "info" | "success";
}

export default function FinanceAgentChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "agent",
      content: "💰 Assalam-o-Alaikum! I'm your Finance Agent. I track payments via Easypaisa, JazzCash, and RAAST. Ask me about payment status, revenue, or transaction history!",
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

    // Simulate finance agent responses
    setTimeout(() => {
      let response = "";
      let type: "payment" | "info" | "success" = "info";

      if (userInput.toLowerCase().includes("payment") || userInput.toLowerCase().includes("status")) {
        response = "💳 Payment Status Summary:\n\n✅ Paid: 45 orders (PKR 1,245,000)\n⏳ Pending: 12 orders (PKR 285,000)\n❌ Failed: 2 orders (PKR 15,000)\n\nPayment Methods:\n• Easypaisa: 25 transactions\n• JazzCash: 18 transactions\n• RAAST: 14 transactions\n• Cash: 2 transactions";
        type = "payment";
      } else if (userInput.toLowerCase().includes("revenue") || userInput.toLowerCase().includes("total")) {
        response = "📊 Revenue Analytics:\n\nToday: PKR 125,000\nThis Week: PKR 845,000\nThis Month: PKR 3,250,000\n\nTop Products:\n1. iPhone 15 - PKR 999,000\n2. MacBook Pro - PKR 1,200,000\n3. iPad Pro - PKR 650,000\n\nProfit Margin: 18.5%";
        type = "success";
      } else if (userInput.toLowerCase().includes("easypaisa") || userInput.toLowerCase().includes("jazzcash")) {
        response = "📱 Mobile Payment Summary:\n\nEasypaisa:\n• Total: PKR 625,000\n• Transactions: 25\n• Success Rate: 96%\n\nJazzCash:\n• Total: PKR 450,000\n• Transactions: 18\n• Success Rate: 94%\n\nAll payments verified and reconciled!";
        type = "payment";
      } else if (userInput.toLowerCase().includes("raast") || userInput.toLowerCase().includes("bank")) {
        response = "🏦 RAAST Payment Summary:\n\nTotal Received: PKR 350,000\nTransactions: 14\nAverage Amount: PKR 25,000\n\nRecent RAAST Payments:\n• Order #1234 - PKR 45,000 ✅\n• Order #1235 - PKR 32,000 ✅\n• Order #1236 - PKR 28,000 ⏳ Pending\n\nAll verified via RAAST API";
        type = "payment";
      } else if (userInput.toLowerCase().includes("pending") || userInput.toLowerCase().includes("unpaid")) {
        response = "⏳ Pending Payments (12 orders):\n\n1. Order #1240 - PKR 25,000 (Easypaisa)\n2. Order #1241 - PKR 18,000 (JazzCash)\n3. Order #1242 - PKR 32,000 (RAAST)\n\nAuto-reminder sent to customers.\nExpected clearance: 24-48 hours";
        type = "info";
      } else {
        response = "I can help you with:\n• Payment status tracking\n• Revenue analytics\n• Easypaisa/JazzCash verification\n• RAAST payment monitoring\n• Pending payment alerts\n\nWhat would you like to check?";
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
    { icon: DollarSign, label: "Payment Status", message: "Show payment status" },
    { icon: TrendingUp, label: "Revenue", message: "Show revenue analytics" },
    { icon: CreditCard, label: "Mobile Payments", message: "Easypaisa and JazzCash summary" },
    { icon: Wallet, label: "RAAST", message: "Show RAAST payments" },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-white to-emerald-50/30 py-8 px-4">
      <div className="container mx-auto max-w-5xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-6"
        >
          <Badge className="mb-4 px-5 py-2 bg-gradient-to-r from-green-600 to-emerald-600 text-white border-0">
            <DollarSign className="w-4 h-4 mr-2" />
            Live AI Agent
          </Badge>
          <h1 className="text-4xl font-bold mb-2 text-green-900">Finance Agent Chat</h1>
          <p className="text-emerald-700">Real-time payment tracking and analytics</p>
        </motion.div>

        {/* Chat Container */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
        >
          <Card className="border-2 border-green-200 shadow-2xl">
            <CardHeader className="bg-gradient-to-r from-green-600 to-emerald-600 text-white">
              <CardTitle className="flex items-center gap-2">
                <DollarSign className="w-5 h-5" />
                Finance Agent - Tracking
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
                              ? "bg-green-600 text-white"
                              : "bg-gradient-to-br from-emerald-500 to-green-600 text-white"
                          }`}
                        >
                          {message.role === "user" ? <User className="w-5 h-5" /> : <DollarSign className="w-5 h-5" />}
                        </div>

                        {/* Message Bubble */}
                        <div
                          className={`rounded-2xl px-4 py-3 ${
                            message.role === "user"
                              ? "bg-green-600 text-white"
                              : message.type === "payment"
                              ? "bg-blue-50 text-blue-900 border-2 border-blue-200"
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
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-500 to-green-600 flex items-center justify-center">
                        <DollarSign className="w-5 h-5 text-white" />
                      </div>
                      <div className="bg-slate-100 rounded-2xl px-4 py-3 border border-slate-200">
                        <div className="flex gap-1">
                          <span className="w-2 h-2 bg-green-600 rounded-full animate-bounce"></span>
                          <span className="w-2 h-2 bg-green-600 rounded-full animate-bounce delay-100"></span>
                          <span className="w-2 h-2 bg-green-600 rounded-full animate-bounce delay-200"></span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Quick Actions */}
              <div className="border-t border-slate-200 p-4 bg-green-50/50">
                <p className="text-xs text-slate-600 mb-2">Quick Actions:</p>
                <div className="flex flex-wrap gap-2">
                  {quickActions.map((action, i) => (
                    <Button
                      key={i}
                      variant="outline"
                      size="sm"
                      onClick={() => setInput(action.message)}
                      className="text-xs border-green-300 hover:bg-green-100"
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
                    placeholder="Ask about payments..."
                    disabled={loading}
                    className="flex-1 h-12 border-2 border-green-300 focus:border-green-600 focus:ring-2 focus:ring-green-600/20 rounded-xl text-base"
                  />
                  <Button
                    onClick={handleSend}
                    disabled={loading || !input.trim()}
                    className="h-12 px-6 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-emerald-600 hover:to-green-600 text-white rounded-xl shadow-lg"
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

