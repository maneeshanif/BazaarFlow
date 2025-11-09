"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Megaphone, Send, Bot, User, Loader2, Sparkles, Facebook, Instagram, Share2 } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "agent";
  content: string;
  timestamp: Date;
  type?: "post" | "info" | "generated";
}

export default function MarketingAgentChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "agent",
      content: "📢 Assalam-o-Alaikum! I'm your Marketing Agent. I create social posts, product descriptions, and promotional content using AI. Ask me to generate content for Facebook, Instagram, or WhatsApp!",
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

    // Simulate marketing agent responses
    setTimeout(() => {
      let response = "";
      let type: "post" | "info" | "generated" = "info";

      if (userInput.toLowerCase().includes("facebook") || userInput.toLowerCase().includes("post")) {
        response = "📱 Facebook Post Generated:\n\n🎉 عید کی خصوصی پیشکش! 🎉\n\niPhone 15 - صرف PKR 285,000\n✨ Latest Model\n✨ 1 Year Warranty\n✨ Free Delivery\n\nآج ہی آرڈر کریں!\n📞 WhatsApp: 0300-1234567\n\n#EidOffer #iPhone15 #TechDeals #Pakistan\n\n[Auto-post scheduled for 6 PM]";
        type = "post";
      } else if (userInput.toLowerCase().includes("instagram") || userInput.toLowerCase().includes("insta")) {
        response = "📸 Instagram Post Generated:\n\n✨ NEW ARRIVAL ✨\n\nMacBook Pro M3\n💻 Ultimate Performance\n🚀 16GB RAM | 512GB SSD\n💰 PKR 450,000\n\n🎁 Limited Time Offer:\n• Free AirPods\n• Free Delivery\n• 1 Year Warranty\n\nDM to order! 📩\n\n#MacBookPro #Apple #TechPakistan #Karachi\n\n[Image: MacBook Pro lifestyle shot]\n[Auto-post scheduled]";
        type = "post";
      } else if (userInput.toLowerCase().includes("product") || userInput.toLowerCase().includes("description")) {
        response = "📝 Product Description Generated:\n\n🎧 AirPods Pro (2nd Gen)\n\nExperience premium sound quality with Apple's latest AirPods Pro. Perfect for music lovers and professionals.\n\n✨ Features:\n• Active Noise Cancellation\n• Transparency Mode\n• Spatial Audio\n• 30 Hours Battery Life\n• Wireless Charging Case\n\n💰 Price: PKR 65,000\n📦 In Stock - Fast Delivery\n🛡️ 1 Year Official Warranty\n\nOrder now via WhatsApp: 0300-1234567\n\n[Optimized for SEO & Social Media]";
        type = "generated";
      } else if (userInput.toLowerCase().includes("promo") || userInput.toLowerCase().includes("sale")) {
        response = "🎯 Promotional Campaign Generated:\n\n🔥 MEGA SALE ALERT 🔥\n\n3 Days Only!\n20% OFF on All Products\n\n📱 Smartphones\n💻 Laptops\n⌚ Smartwatches\n🎧 Audio Devices\n\n💳 Payment Options:\n• Easypaisa\n• JazzCash\n• Cash on Delivery\n\n⏰ Sale Ends: Sunday Midnight\n\n📞 Order Now: 0300-1234567\n🌐 Visit: www.bazaarflow.pk\n\n#MegaSale #TechDeals #Pakistan\n\n[Multi-platform campaign ready]";
        type = "post";
      } else if (userInput.toLowerCase().includes("whatsapp") || userInput.toLowerCase().includes("message")) {
        response = "💬 WhatsApp Broadcast Message:\n\nالسلام علیکم! 🌙\n\nعید کی خصوصی پیشکش!\n\n📱 iPhone 15 - PKR 285,000\n💻 MacBook Pro - PKR 450,000\n📱 iPad Pro - PKR 195,000\n\n🎁 Free Gifts:\n✅ Screen Protector\n✅ Phone Case\n✅ Free Delivery\n\nآرڈر کے لیے رابطہ کریں:\n📞 0300-1234567\n\nشکریہ! 🙏\n\n[Ready to send to 500+ customers]";
        type = "generated";
      } else if (userInput.toLowerCase().includes("urdu") || userInput.toLowerCase().includes("اردو")) {
        response = "📱 اردو مارکیٹنگ پوسٹ:\n\n🎉 نئی آمد! 🎉\n\niPhone 15 Pro Max\n\n✨ خصوصیات:\n• 256GB Storage\n• A17 Pro Chip\n• Titanium Design\n• 48MP Camera\n\n💰 قیمت: PKR 385,000\n\n🎁 مفت تحائف:\n✅ AirPods\n✅ Screen Guard\n✅ ڈیلیوری\n\nآرڈر کے لیے:\n📞 WhatsApp: 0300-1234567\n\n#iPhone15ProMax #ٹیکنالوجی #پاکستان\n\n[سوشل میڈیا کے لیے تیار]";
        type = "post";
      } else {
        response = "I can generate:\n• Facebook posts (Urdu/English)\n• Instagram captions\n• Product descriptions\n• Promotional campaigns\n• WhatsApp broadcasts\n• Social media content\n\nWhat would you like me to create?";
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
    }, 2000);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const quickActions = [
    { icon: Facebook, label: "Facebook Post", message: "Create a Facebook post for iPhone 15" },
    { icon: Instagram, label: "Instagram Post", message: "Create Instagram post for MacBook Pro" },
    { icon: Sparkles, label: "Product Desc", message: "Generate product description for AirPods Pro" },
    { icon: Share2, label: "Promo Campaign", message: "Create promotional sale campaign" },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-50 via-white to-rose-50/30 py-8 px-4">
      <div className="container mx-auto max-w-5xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-6"
        >
          <Badge className="mb-4 px-5 py-2 bg-gradient-to-r from-pink-600 to-rose-600 text-white border-0">
            <Megaphone className="w-4 h-4 mr-2" />
            Live AI Agent
          </Badge>
          <h1 className="text-4xl font-bold mb-2 text-pink-900">Marketing Agent Chat</h1>
          <p className="text-rose-700">AI-powered content generation for social media</p>
        </motion.div>

        {/* Chat Container */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
        >
          <Card className="border-2 border-pink-200 shadow-2xl">
            <CardHeader className="bg-gradient-to-r from-pink-600 to-rose-600 text-white">
              <CardTitle className="flex items-center gap-2">
                <Megaphone className="w-5 h-5" />
                Marketing Agent - Creating
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
                              ? "bg-pink-600 text-white"
                              : "bg-gradient-to-br from-rose-500 to-pink-600 text-white"
                          }`}
                        >
                          {message.role === "user" ? <User className="w-5 h-5" /> : <Megaphone className="w-5 h-5" />}
                        </div>

                        {/* Message Bubble */}
                        <div
                          className={`rounded-2xl px-4 py-3 ${
                            message.role === "user"
                              ? "bg-pink-600 text-white"
                              : message.type === "post"
                              ? "bg-gradient-to-br from-pink-50 to-rose-50 text-pink-900 border-2 border-pink-200"
                              : message.type === "generated"
                              ? "bg-purple-50 text-purple-900 border-2 border-purple-200"
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
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-rose-500 to-pink-600 flex items-center justify-center">
                        <Sparkles className="w-5 h-5 text-white animate-pulse" />
                      </div>
                      <div className="bg-slate-100 rounded-2xl px-4 py-3 border border-slate-200">
                        <div className="flex gap-1 items-center">
                          <Sparkles className="w-3 h-3 text-pink-600 animate-spin" />
                          <span className="text-xs text-slate-600 ml-2">Generating content...</span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Quick Actions */}
              <div className="border-t border-slate-200 p-4 bg-pink-50/50">
                <p className="text-xs text-slate-600 mb-2">Quick Actions:</p>
                <div className="flex flex-wrap gap-2">
                  {quickActions.map((action, i) => (
                    <Button
                      key={i}
                      variant="outline"
                      size="sm"
                      onClick={() => setInput(action.message)}
                      className="text-xs border-pink-300 hover:bg-pink-100"
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
                    placeholder="Ask me to create content..."
                    disabled={loading}
                    className="flex-1 h-12 border-2 border-pink-300 focus:border-pink-600 focus:ring-2 focus:ring-pink-600/20 rounded-xl text-base"
                  />
                  <Button
                    onClick={handleSend}
                    disabled={loading || !input.trim()}
                    className="h-12 px-6 bg-gradient-to-r from-pink-600 to-rose-600 hover:from-rose-600 hover:to-pink-600 text-white rounded-xl shadow-lg"
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

