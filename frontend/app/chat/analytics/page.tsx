"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { BarChart3, Send, Bot, User, Loader2, TrendingUp, PieChart, Globe } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "agent";
  content: string;
  timestamp: Date;
  language?: "english" | "urdu";
}

export default function AnalyticsAgentChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "agent",
      content: "📊 السلام علیکم! میں آپ کا Analytics Agent ہوں۔ I generate weekly reports in Urdu/English, predict demand, and advise pricing. Ask me for insights!",
      timestamp: new Date(),
      language: "urdu",
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

    // Simulate analytics agent responses
    setTimeout(() => {
      let response = "";
      let language: "english" | "urdu" = "english";

      if (userInput.toLowerCase().includes("report") || userInput.toLowerCase().includes("summary")) {
        response = "📈 ہفتہ وار رپورٹ (Weekly Report):\n\n🛍️ کل فروخت (Total Sales): PKR 845,000\n📦 آرڈرز (Orders): 59\n👥 نئے گاہک (New Customers): 23\n\nTop Products:\n1. iPhone 15 - 15 units\n2. MacBook Pro - 8 units\n3. iPad Pro - 12 units\n\n📊 Growth: +18% from last week\n💡 Recommendation: Stock up on iPhone 15";
        language = "urdu";
      } else if (userInput.toLowerCase().includes("predict") || userInput.toLowerCase().includes("demand") || userInput.toLowerCase().includes("forecast")) {
        response = "🔮 Demand Prediction (Next 7 Days):\n\niPhone 15:\n• Expected Demand: +25%\n• Reason: Eid shopping season\n• Suggested Stock: 30 units\n\nMacBook Pro:\n• Expected Demand: +10%\n• Reason: Corporate purchases\n• Suggested Stock: 15 units\n\niPad Pro:\n• Expected Demand: +30%\n• Reason: Back to school\n• Suggested Stock: 25 units\n\n💡 AI Confidence: 87%";
        language = "english";
      } else if (userInput.toLowerCase().includes("price") || userInput.toLowerCase().includes("pricing")) {
        response = "💰 قیمت کی سفارشات (Pricing Recommendations):\n\niPhone 15:\n• Current: PKR 285,000\n• Suggested: PKR 289,000 (+1.4%)\n• Reason: High demand, low stock\n\nMacBook Pro:\n• Current: PKR 450,000\n• Suggested: PKR 445,000 (-1.1%)\n• Reason: Competitor pricing\n\niPad Pro:\n• Current: PKR 195,000\n• Suggested: PKR 199,000 (+2%)\n• Reason: Premium positioning\n\n📈 Expected Revenue Impact: +PKR 45,000/week";
        language = "urdu";
      } else if (userInput.toLowerCase().includes("customer") || userInput.toLowerCase().includes("گاہک")) {
        response = "👥 Customer Analytics:\n\nTotal Customers: 234\nActive This Week: 89\nNew Customers: 23\nReturning Rate: 68%\n\nTop Customers:\n1. Ali Khan - PKR 125,000 (5 orders)\n2. Sara Ahmed - PKR 98,000 (4 orders)\n3. Hassan Raza - PKR 87,000 (3 orders)\n\n💡 Insight: Focus on customer retention programs";
        language = "english";
      } else if (userInput.toLowerCase().includes("urdu") || userInput.toLowerCase().includes("اردو")) {
        response = "📊 تجزیاتی خلاصہ (Analytics Summary):\n\n🎯 کارکردگی (Performance):\n• فروخت: PKR 3.2M اس ماہ\n• منافع: 18.5%\n• آرڈرز: 245\n\n📈 رجحانات (Trends):\n• موبائل فونز: سب سے زیادہ فروخت\n• لیپ ٹاپس: دوسرے نمبر پر\n• ٹیبلٹس: تیسرے نمبر پر\n\n💡 سفارش: موبائل فونز کا اسٹاک بڑھائیں";
        language = "urdu";
      } else {
        response = "I can help you with:\n• Weekly reports (Urdu/English)\n• Demand predictions\n• Pricing recommendations\n• Customer analytics\n• Sales trends\n\nمیں آپ کی مدد کر سکتا ہوں!\nWhat would you like to analyze?";
        language = "english";
      }

      const agentMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        content: response,
        timestamp: new Date(),
        language,
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
    { icon: BarChart3, label: "Weekly Report", message: "Generate weekly report in Urdu" },
    { icon: TrendingUp, label: "Predictions", message: "Predict demand for next week" },
    { icon: PieChart, label: "Pricing", message: "Show pricing recommendations" },
    { icon: Globe, label: "Customer Insights", message: "Show customer analytics" },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-indigo-50/30 py-8 px-4">
      <div className="container mx-auto max-w-5xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-6"
        >
          <Badge className="mb-4 px-5 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white border-0">
            <BarChart3 className="w-4 h-4 mr-2" />
            Live AI Agent
          </Badge>
          <h1 className="text-4xl font-bold mb-2 text-purple-900">Analytics Agent Chat</h1>
          <p className="text-indigo-700">Bilingual reports and demand predictions</p>
        </motion.div>

        {/* Chat Container */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
        >
          <Card className="border-2 border-purple-200 shadow-2xl">
            <CardHeader className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white">
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                Analytics Agent - Analyzing
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
                              ? "bg-purple-600 text-white"
                              : "bg-gradient-to-br from-indigo-500 to-purple-600 text-white"
                          }`}
                        >
                          {message.role === "user" ? <User className="w-5 h-5" /> : <BarChart3 className="w-5 h-5" />}
                        </div>

                        {/* Message Bubble */}
                        <div
                          className={`rounded-2xl px-4 py-3 ${
                            message.role === "user"
                              ? "bg-purple-600 text-white"
                              : message.language === "urdu"
                              ? "bg-indigo-50 text-indigo-900 border-2 border-indigo-200"
                              : "bg-slate-100 text-slate-900 border border-slate-200"
                          }`}
                        >
                          <p className="text-sm leading-relaxed whitespace-pre-line" style={{ direction: message.language === "urdu" ? "rtl" : "ltr" }}>
                            {message.content}
                          </p>
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
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                        <BarChart3 className="w-5 h-5 text-white" />
                      </div>
                      <div className="bg-slate-100 rounded-2xl px-4 py-3 border border-slate-200">
                        <div className="flex gap-1">
                          <span className="w-2 h-2 bg-purple-600 rounded-full animate-bounce"></span>
                          <span className="w-2 h-2 bg-purple-600 rounded-full animate-bounce delay-100"></span>
                          <span className="w-2 h-2 bg-purple-600 rounded-full animate-bounce delay-200"></span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Quick Actions */}
              <div className="border-t border-slate-200 p-4 bg-purple-50/50">
                <p className="text-xs text-slate-600 mb-2">Quick Actions:</p>
                <div className="flex flex-wrap gap-2">
                  {quickActions.map((action, i) => (
                    <Button
                      key={i}
                      variant="outline"
                      size="sm"
                      onClick={() => setInput(action.message)}
                      className="text-xs border-purple-300 hover:bg-purple-100"
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
                    placeholder="Ask in English or Urdu..."
                    disabled={loading}
                    className="flex-1 h-12 border-2 border-purple-300 focus:border-purple-600 focus:ring-2 focus:ring-purple-600/20 rounded-xl text-base"
                  />
                  <Button
                    onClick={handleSend}
                    disabled={loading || !input.trim()}
                    className="h-12 px-6 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-indigo-600 hover:to-purple-600 text-white rounded-xl shadow-lg"
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

