"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MessageSquare, Send, Bot, User, Loader2, Sparkles, CheckCircle2, Package, DollarSign } from "lucide-react";
import axios from "axios";

interface Message {
  id: string;
  role: "user" | "agent";
  content: string;
  timestamp: Date;
  status?: "sending" | "sent" | "error";
}

export default function SalesAgentChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "agent",
      content: "👋 Assalam-o-Alaikum! I'm your AI Sales Agent. How can I help you today? Ask me about products, prices, or place an order!",
      timestamp: new Date(),
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
      status: "sent",
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      // Call backend API
      const response = await axios.post(`${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/api/chat/sales`, {
        message: input,
        session_id: typeof window !== 'undefined' ? `web-user-${Date.now()}` : 'web-user-session',
      });

      const agentMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        content: response.data.response || "I'm processing your request...",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, agentMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        content: "Sorry, I'm having trouble connecting. Please try again or use WhatsApp at +92 300 1234567",
        timestamp: new Date(),
        status: "error",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const quickActions = [
    { icon: Package, label: "Show Products", message: "Show me all products" },
    { icon: DollarSign, label: "Price Range", message: "Products under 2000 PKR" },
    { icon: MessageSquare, label: "Place Order", message: "I want to place an order" },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30 py-8 px-4">
      <div className="container mx-auto max-w-5xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-6"
        >
          <Badge className="mb-4 px-5 py-2 bg-gradient-to-r from-[#174143] to-[#427A76] text-white border-0">
            <Bot className="w-4 h-4 mr-2" />
            Live AI Agent
          </Badge>
          <h1 className="text-4xl font-bold mb-2 text-[#174143]">Sales Agent Chat</h1>
          <p className="text-[#427A76]">Real-time conversation with our AI Sales Agent</p>
        </motion.div>

        {/* Chat Container */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
        >
          <Card className="border-2 border-[#427A76]/20 shadow-2xl">
            <CardHeader className="bg-gradient-to-r from-[#174143] to-[#427A76] text-white">
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="w-5 h-5" />
                Sales Agent - Online
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
                              ? "bg-[#174143] text-white"
                              : "bg-gradient-to-br from-[#427A76] to-[#174143] text-white"
                          }`}
                        >
                          {message.role === "user" ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
                        </div>

                        {/* Message Bubble */}
                        <div
                          className={`rounded-2xl px-4 py-3 ${
                            message.role === "user"
                              ? "bg-[#174143] text-white"
                              : "bg-slate-100 text-slate-900 border border-slate-200"
                          }`}
                        >
                          <p className="text-sm leading-relaxed">{message.content}</p>
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
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#427A76] to-[#174143] flex items-center justify-center">
                        <Bot className="w-5 h-5 text-white" />
                      </div>
                      <div className="bg-slate-100 rounded-2xl px-4 py-3 border border-slate-200">
                        <div className="flex gap-1">
                          <span className="w-2 h-2 bg-[#427A76] rounded-full animate-bounce"></span>
                          <span className="w-2 h-2 bg-[#427A76] rounded-full animate-bounce delay-100"></span>
                          <span className="w-2 h-2 bg-[#427A76] rounded-full animate-bounce delay-200"></span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Quick Actions */}
              <div className="border-t border-slate-200 p-4 bg-slate-50">
                <p className="text-xs text-slate-600 mb-2">Quick Actions:</p>
                <div className="flex flex-wrap gap-2">
                  {quickActions.map((action, i) => (
                    <Button
                      key={i}
                      variant="outline"
                      size="sm"
                      onClick={() => setInput(action.message)}
                      className="text-xs border-[#427A76]/30 hover:bg-[#427A76]/10"
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
                    placeholder="Type your message..."
                    disabled={loading}
                    className="flex-1 h-12 border-2 border-[#427A76]/30 focus:border-[#174143] focus:ring-2 focus:ring-[#174143]/20 rounded-xl text-base"
                  />
                  <Button
                    onClick={handleSend}
                    disabled={loading || !input.trim()}
                    className="h-12 px-6 bg-gradient-to-r from-[#174143] to-[#427A76] hover:from-[#427A76] hover:to-[#174143] text-white rounded-xl shadow-lg"
                  >
                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Info Cards */}
        <div className="grid md:grid-cols-3 gap-4 mt-6">
          {[
            { icon: MessageSquare, title: "Natural Language", desc: "Chat in Urdu or English" },
            { icon: Sparkles, title: "AI Powered", desc: "Intelligent product recommendations" },
            { icon: CheckCircle2, title: "Instant Response", desc: "Real-time order processing" },
          ].map((item, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 + i * 0.1 }}
            >
              <Card className="border-[#427A76]/20 bg-white/80 backdrop-blur">
                <CardContent className="p-4 flex items-center gap-3">
                  <div className="w-10 h-10 bg-[#174143]/10 rounded-lg flex items-center justify-center">
                    <item.icon className="w-5 h-5 text-[#174143]" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-sm text-[#174143]">{item.title}</h3>
                    <p className="text-xs text-[#427A76]">{item.desc}</p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}

