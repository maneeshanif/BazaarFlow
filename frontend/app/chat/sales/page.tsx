"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { MessageSquare, Send, Bot, User, Loader2, Sparkles, CheckCircle2, Package, DollarSign, ShoppingBag, ShoppingCart, TrendingUp, History, Clock } from "lucide-react";
import axios from "axios";
import confetti from "canvas-confetti";
import { toast } from "sonner";

interface Message {
  id: string;
  role: "user" | "agent";
  content: string;
  timestamp: Date;
  status?: "sending" | "sent" | "error";
  isOrderPlaced?: boolean;
}

interface OrderSummary {
  id: string;
  customer: string;
  items: string;
  amount: string;
  time: string;
}

export default function SalesAgentChatPage() {
  const [sessionId] = useState(() => 
    typeof window !== 'undefined' ? `web-user-${Date.now()}` : 'web-user-session'
  );
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
  const [recentOrders, setRecentOrders] = useState<OrderSummary[]>([]);
  const [orderCount, setOrderCount] = useState(0);
  const [userScrolled, setUserScrolled] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (messagesEndRef.current && !userScrolled) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  };

  // Track user scroll behavior
  const handleScroll = () => {
    if (messagesContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = messagesContainerRef.current;
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
      setUserScrolled(!isAtBottom);
    }
  };

  useEffect(() => {
    // Only auto-scroll on initial load (first message)
    if (messages.length === 1) {
      scrollToBottom();
    }
  }, []);

  useEffect(() => {
    // Only scroll if user hasn't manually scrolled up
    if (!userScrolled && messages.length > 1) {
      scrollToBottom();
    }
  }, [messages, userScrolled]);

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
    const userInput = input;
    setInput("");
    setUserScrolled(false); // Reset scroll state when sending message
    setLoading(true);

    try {
      const response = await axios.post(`${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/api/chat/sales`, {
        message: userInput,
        session_id: sessionId,
      });

      const agentResponse = response.data.response || "I'm processing your request...";
      
      const agentMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        content: agentResponse,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, agentMessage]);

      // Enhanced order detection - check multiple patterns
      const responseText = agentResponse.toLowerCase();
      const orderKeywords = [
        "order placed",
        "order confirmed", 
        "order created",
        "successfully created your order",
        "order has been created",
        "order successfully",
        "placed your order",
        "order #",
        "order id"
      ];
      
      const isOrderPlaced = orderKeywords.some(keyword => responseText.includes(keyword));
      
      if (isOrderPlaced) {
        // Mark message as order placed
        agentMessage.isOrderPlaced = true;
        
        // Trigger confetti celebration
        confetti({
          particleCount: 150,
          spread: 100,
          origin: { y: 0.6 },
          colors: ['#174143', '#427A76', '#22c55e', '#10b981', '#fbbf24']
        });
        
        // Show success toast
        toast.success("🎉 Order Placed Successfully!", {
          description: "Your order has been confirmed and will be processed soon.",
          duration: 5000,
        });

        // Update order count
        setOrderCount(prev => prev + 1);

        // Extract order details and add to recent orders
        const orderIdMatch = agentResponse.match(/order\s*#?\s*(\d+)/i);
        if (orderIdMatch) {
          const newOrder: OrderSummary = {
            id: `#ORD-${orderIdMatch[1].padStart(3, '0')}`,
            customer: "You",
            items: "View in orders",
            amount: "PKR -",
            time: "Just now"
          };
          setRecentOrders(prev => [newOrder, ...prev.slice(0, 4)]);
        }
      }
    } catch {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        content: "Sorry, I'm having trouble connecting. Please try again or use WhatsApp at +92 300 1234567",
        timestamp: new Date(),
        status: "error",
      };
      setMessages((prev) => [...prev, errorMessage]);
      
      toast.error("Connection Error", {
        description: "Failed to send message. Please try again.",
      });
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
    { icon: DollarSign, label: "Price Range", message: "Products under 200000 PKR" },
    { icon: MessageSquare, label: "Place Order", message: "I want to place an order" },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 py-8 px-4">
      <div className="container mx-auto max-w-7xl">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-6"
        >
          <Badge className="mb-4 px-5 py-2 bg-gradient-to-r from-[#174143] to-[#427A76] text-white border-0 shadow-lg">
            <Bot className="w-4 h-4 mr-2" />
            Live AI Agent
          </Badge>
          <h1 className="text-4xl md:text-5xl font-bold mb-2 bg-gradient-to-r from-[#174143] to-[#427A76] bg-clip-text text-transparent">
            Sales Agent Chat
          </h1>
          <p className="text-slate-600 dark:text-slate-400">Real-time conversation with our AI Sales Agent</p>
        </motion.div>

        {/* Split Layout: Sidebar (30%) + Chat (70%) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Sidebar - 30% on large screens */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="lg:col-span-4 space-y-6"
          >
            {/* Stats Card */}
            <Card className="border-2 border-slate-200 dark:border-slate-700 shadow-lg backdrop-blur-lg bg-white/95 dark:bg-slate-800/95 rounded-2xl">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-[#427A76]" />
                  Session Stats
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between p-3 bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-xl border border-green-200 dark:border-green-800">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-green-600 to-emerald-600 rounded-lg flex items-center justify-center shadow-sm">
                      <ShoppingCart className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <p className="text-xs text-slate-600 dark:text-slate-400">Orders Placed</p>
                      <p className="text-2xl font-bold text-slate-900 dark:text-white">{orderCount}</p>
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-gradient-to-br from-blue-50 to-cyan-50 dark:from-blue-900/20 dark:to-cyan-900/20 rounded-xl border border-blue-200 dark:border-blue-800">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-cyan-600 rounded-lg flex items-center justify-center shadow-sm">
                      <MessageSquare className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <p className="text-xs text-slate-600 dark:text-slate-400">Messages</p>
                      <p className="text-2xl font-bold text-slate-900 dark:text-white">{messages.length}</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Recent Orders Card */}
            <Card className="border-2 border-slate-200 dark:border-slate-700 shadow-lg backdrop-blur-lg bg-white/95 dark:bg-slate-800/95 rounded-2xl">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                  <History className="w-5 h-5 text-[#427A76]" />
                  Recent Orders
                </CardTitle>
              </CardHeader>
              <CardContent>
                {recentOrders.length > 0 ? (
                  <div className="space-y-3">
                    {recentOrders.map((order) => (
                      <motion.div
                        key={order.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="p-3 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-700 dark:to-slate-600 rounded-xl border border-slate-200 dark:border-slate-600 hover:shadow-md transition-all"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <Badge className="text-xs bg-gradient-to-r from-[#174143] to-[#427A76] text-white">
                            {order.id}
                          </Badge>
                          <span className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {order.time}
                          </span>
                        </div>
                        <p className="text-sm font-medium text-slate-900 dark:text-white">{order.items}</p>
                        <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">{order.customer}</p>
                      </motion.div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <ShoppingBag className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
                    <p className="text-sm text-slate-500 dark:text-slate-400">No orders yet</p>
                    <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">Place your first order to see it here!</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Quick Tips */}
            <Card className="border-2 border-purple-200 dark:border-purple-800 shadow-lg backdrop-blur-lg bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-2xl">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg font-semibold flex items-center gap-2 text-purple-900 dark:text-purple-100">
                  <Sparkles className="w-5 h-5" />
                  Quick Tips
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-slate-700 dark:text-slate-300">
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-purple-600 dark:text-purple-400 mt-0.5 flex-shrink-0" />
                    <span>Ask about product prices and availability</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-purple-600 dark:text-purple-400 mt-0.5 flex-shrink-0" />
                    <span>Place orders with customer details</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-purple-600 dark:text-purple-400 mt-0.5 flex-shrink-0" />
                    <span>Chat in English or Urdu</span>
                  </li>
                </ul>
              </CardContent>
            </Card>
          </motion.div>

          {/* Main Chat Area - 70% on large screens */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
            className="lg:col-span-8"
          >
          <Card className="border-2 border-slate-200 dark:border-slate-700 shadow-2xl backdrop-blur-lg bg-white/95 dark:bg-slate-800/95 rounded-3xl overflow-hidden">
            <CardHeader className="bg-gradient-to-r from-[#174143] to-[#427A76] text-white p-6">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-3 text-xl">
                  <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                    <Bot className="w-7 h-7" />
                  </div>
                  <div>
                    <div className="font-bold">Sales Agent</div>
                    <div className="text-xs text-white/80 font-normal">Always ready to help</div>
                  </div>
                </CardTitle>
                <div className="flex items-center gap-2 bg-white/20 px-4 py-2 rounded-full backdrop-blur-sm">
                  <span className="w-2.5 h-2.5 bg-green-400 rounded-full animate-pulse shadow-lg shadow-green-400/50"></span>
                  <span className="text-sm font-medium">Online</span>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {/* Messages Area with WhatsApp-style emoji background */}
              <div 
                ref={messagesContainerRef}
                onScroll={handleScroll}
                className="h-[450px] overflow-y-auto p-6 space-y-4 relative"
                style={{
                  backgroundColor: '#efeae2',
                  backgroundImage: `
                    url("data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Ctext x='10' y='30' font-size='20' opacity='0.03'%3E😊%3C/text%3E%3Ctext x='60' y='25' font-size='16' opacity='0.03'%3E🎉%3C/text%3E%3Ctext x='35' y='70' font-size='18' opacity='0.03'%3E💬%3C/text%3E%3Ctext x='75' y='65' font-size='22' opacity='0.03'%3E✨%3C/text%3E%3Ctext x='15' y='90' font-size='16' opacity='0.03'%3E📦%3C/text%3E%3Ctext x='85' y='45' font-size='20' opacity='0.03'%3E🛒%3C/text%3E%3Ctext x='45' y='15' font-size='18' opacity='0.03'%3E💰%3C/text%3E%3Ctext x='25' y='55' font-size='16' opacity='0.03'%3E🤝%3C/text%3E%3C/svg%3E")
                  `,
                  backgroundSize: '200px 200px',
                  backgroundRepeat: 'repeat'
                }}
              >
                {/* Dark mode overlay */}
                <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-transparent dark:from-slate-900/80 dark:via-slate-900/80 dark:to-slate-900/80 pointer-events-none" />
                
                <div className="relative z-10">
                <AnimatePresence mode="popLayout">
                  {messages.map((message) => (
                    <motion.div
                      key={message.id}
                      initial={{ opacity: 0, y: 20, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      transition={{ type: "spring", duration: 0.5 }}
                      className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={`flex gap-3 max-w-[85%] ${
                          message.role === "user" ? "flex-row-reverse" : "flex-row"
                        }`}
                      >
                        <motion.div
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          transition={{ type: "spring", delay: 0.1 }}
                          className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 shadow-lg ${
                            message.role === "user"
                              ? "bg-gradient-to-br from-[#174143] to-[#0d2526] text-white"
                              : "bg-gradient-to-br from-[#427A76] to-[#174143] text-white ring-2 ring-white dark:ring-slate-800"
                          }`}
                        >
                          {message.role === "user" ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
                        </motion.div>

                        <div className="flex flex-col gap-1">
                          <motion.div
                            initial={{ scale: 0.9 }}
                            animate={{ scale: 1 }}
                            className={`rounded-2xl px-5 py-3 shadow-md ${
                              message.role === "user"
                                ? "bg-gradient-to-br from-[#174143] to-[#0d2526] text-white rounded-tr-sm"
                                : "bg-white dark:bg-slate-700 text-slate-900 dark:text-white border-2 border-slate-100 dark:border-slate-600 rounded-tl-sm"
                            }`}
                          >
                            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
                          </motion.div>
                          <p
                            className={`text-xs px-2 ${
                              message.role === "user" ? "text-slate-500 text-right" : "text-slate-500"
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
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex justify-start"
                  >
                    <div className="flex gap-3 max-w-[80%]">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#427A76] to-[#174143] flex items-center justify-center shadow-lg">
                        <Bot className="w-5 h-5 text-white" />
                      </div>
                      <div className="bg-white dark:bg-slate-700 rounded-2xl rounded-tl-sm px-5 py-4 border-2 border-slate-100 dark:border-slate-600 shadow-md">
                        <div className="flex gap-1.5">
                          <motion.span
                            className="w-2 h-2 bg-[#427A76] rounded-full"
                            animate={{ scale: [1, 1.3, 1], opacity: [1, 0.5, 1] }}
                            transition={{ duration: 1, repeat: Infinity, delay: 0 }}
                          />
                          <motion.span
                            className="w-2 h-2 bg-[#427A76] rounded-full"
                            animate={{ scale: [1, 1.3, 1], opacity: [1, 0.5, 1] }}
                            transition={{ duration: 1, repeat: Infinity, delay: 0.2 }}
                          />
                          <motion.span
                            className="w-2 h-2 bg-[#427A76] rounded-full"
                            animate={{ scale: [1, 1.3, 1], opacity: [1, 0.5, 1] }}
                            transition={{ duration: 1, repeat: Infinity, delay: 0.4 }}
                          />
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}

                <div ref={messagesEndRef} />
                </div>
              </div>

              {/* Quick Actions */}
              <div className="border-t-2 border-slate-200 dark:border-slate-700 px-6 py-4 bg-slate-50/50 dark:bg-slate-800/50 backdrop-blur-sm">
                <p className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-3">Quick Actions</p>
                <div className="flex flex-wrap gap-2">
                  {quickActions.map((action, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: 0.5 + i * 0.1 }}
                    >
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setInput(action.message)}
                        className="text-xs border-2 border-slate-200 dark:border-slate-600 hover:border-[#427A76] hover:bg-[#427A76]/5 dark:hover:bg-[#427A76]/10 transition-all rounded-xl shadow-sm"
                      >
                        <action.icon className="w-3.5 h-3.5 mr-1.5" />
                        {action.label}
                      </Button>
                    </motion.div>
                  ))}
                </div>
              </div>

              {/* Input Area */}
              <div className="border-t-2 border-slate-200 dark:border-slate-700 p-6 bg-white dark:bg-slate-800">
                <div className="flex gap-3">
                  <Input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Type your message here..."
                    disabled={loading}
                    className="flex-1 h-14 border-2 border-slate-300 dark:border-slate-600 focus:border-[#174143] dark:focus:border-[#427A76] focus:ring-2 focus:ring-[#174143]/20 dark:focus:ring-[#427A76]/20 rounded-2xl text-base px-5 shadow-sm transition-all"
                  />
                  <Button
                    onClick={handleSend}
                    disabled={loading || !input.trim()}
                    className="h-14 px-8 bg-gradient-to-r from-[#174143] to-[#427A76] hover:from-[#0d2526] hover:to-[#174143] text-white rounded-2xl shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Send className="w-5 h-5" />
                    )}
                  </Button>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-3 text-center">
                  Press <kbd className="px-2 py-1 bg-slate-200 dark:bg-slate-700 rounded">Enter</kbd> to send
                </p>
              </div>
            </CardContent>
          </Card>
          </motion.div>
        </div>

        {/* Feature Cards - Full Width Below */}
        <div className="grid md:grid-cols-3 gap-4 mt-6">
          {[
            { icon: MessageSquare, title: "Natural Language", desc: "Chat in Urdu or English", color: "from-blue-600 to-cyan-600" },
            { icon: Sparkles, title: "AI Powered", desc: "Intelligent product recommendations", color: "from-purple-600 to-pink-600" },
            { icon: CheckCircle2, title: "Instant Response", desc: "Real-time order processing", color: "from-green-600 to-emerald-600" },
          ].map((item, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 + i * 0.1 }}
            >
              <Card className="border-2 border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/80 backdrop-blur-lg hover:shadow-lg transition-shadow rounded-2xl">
                <CardContent className="p-4 flex items-center gap-3">
                  <div className={`w-12 h-12 bg-gradient-to-br ${item.color} rounded-xl flex items-center justify-center shadow-lg`}>
                    <item.icon className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-sm text-slate-900 dark:text-white">{item.title}</h3>
                    <p className="text-xs text-slate-600 dark:text-slate-400">{item.desc}</p>
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
