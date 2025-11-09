"use client";

import { useState } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import Image from "next/image";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ShoppingCart, User, Phone, Package, DollarSign, MapPin, FileText, CheckCircle2, AlertCircle, Loader2, Sparkles, MessageSquare, Zap } from "lucide-react";

export default function SalesFormPage() {
  const [form, setForm] = useState({
    customer_name: "",
    customer_phone: "",
    product_id: "",
    product_name: "",
    quantity: 1,
    budget: "",
    payment_status: "pending",
    delivery_address: "",
    notes: "",
  });

  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  function onChange(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: name === "quantity" ? Number(value) : value }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setStatus(null);
    setSuccess(false);
    try {
      const res = await axios.post("http://localhost:8000/api/sales", form, {
        headers: { "Content-Type": "application/json" },
      });
      if (res.status === 201) {
        setStatus("Order created successfully (ID: " + res.data.order.id + ")");
        setSuccess(true);
        setForm({
          customer_name: "",
          customer_phone: "",
          product_id: "",
          product_name: "",
          quantity: 1,
          budget: "",
          payment_status: "pending",
          delivery_address: "",
          notes: "",
        });
      }
    } catch (err: unknown) {
      const getMsg = (e: unknown) => {
        if (typeof e === "object" && e !== null) {
          const anyE = e as any;
          return anyE?.response?.data?.detail || anyE?.message || String(e);
        }
        return String(e);
      };
      setStatus("Error: " + getMsg(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Hero Section */}
      <section className="py-12 px-4 bg-gradient-to-br from-slate-50 to-white border-b">
        <div className="container mx-auto max-w-7xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center"
          >
            <Badge className="mb-4 px-5 py-2.5 bg-gradient-to-r from-[#174143] to-[#427A76] text-white border-0 shadow-lg">
              <MessageSquare className="w-4 h-4 mr-2" />
              AI Sales Agent Demo
            </Badge>
            <h1 className="text-4xl md:text-5xl font-bold mb-3 bg-gradient-to-br from-slate-900 to-slate-700 bg-clip-text text-transparent">
              Create Your First Order
            </h1>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              Watch our AI Sales Agent process your order autonomously
            </p>
          </motion.div>
        </div>
      </section>

      {/* Main Content - Improved Layout */}
      <section className="py-12 px-4">
        <div className="container mx-auto max-w-6xl">
          <div className="grid lg:grid-cols-3 gap-8">
            {/* Left Side - Form (Wider) */}
            <div className="lg:col-span-2">
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
              >
                <Card className="border-2 border-slate-200 shadow-2xl rounded-2xl overflow-hidden">
                  <CardHeader className="bg-gradient-to-r from-[#174143] to-[#427A76] text-white">
                    <CardTitle className="flex items-center gap-2 text-xl">
                      <Package className="w-6 h-6" />
                      Order Details
                    </CardTitle>
                    <CardDescription className="text-white/90">
                      Fill in the customer and product information below
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-8">
                    <form onSubmit={onSubmit} className="space-y-6">
                      {/* Customer Information */}
                      <div className="space-y-4">
                        <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                          <User className="w-5 h-5 text-[#427A76]" />
                          Customer Information
                        </h3>
                        <div className="grid md:grid-cols-2 gap-6">
                          <div className="space-y-2">
                            <Label htmlFor="customer_name" className="text-slate-700 font-semibold">Customer Name</Label>
                            <Input
                              id="customer_name"
                              name="customer_name"
                              value={form.customer_name}
                              onChange={onChange}
                              placeholder="Enter customer name"
                              required
                              className="h-12 border-2 border-slate-300 focus:border-[#174143] focus:ring-2 focus:ring-[#174143]/20 rounded-lg"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label htmlFor="customer_phone" className="text-slate-700 font-semibold">Phone Number</Label>
                            <Input
                              id="customer_phone"
                              name="customer_phone"
                              value={form.customer_phone}
                              onChange={onChange}
                              placeholder="+92 300 1234567"
                              required
                              className="h-12 border-2 border-slate-300 focus:border-[#174143] focus:ring-2 focus:ring-[#174143]/20 rounded-lg"
                            />
                          </div>
                        </div>
                      </div>

                      {/* Product Information */}
                      <div className="space-y-4">
                        <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                          <Package className="w-5 h-5 text-[#427A76]" />
                          Product Information
                        </h3>
                        <div className="grid md:grid-cols-2 gap-6">
                          <div className="space-y-2">
                            <Label htmlFor="product_id" className="text-slate-700 font-semibold">Product ID</Label>
                            <Input
                              id="product_id"
                              name="product_id"
                              value={form.product_id}
                              onChange={onChange}
                              placeholder="e.g., PROD-001"
                              required
                              className="h-12 border-2 border-slate-300 focus:border-[#174143] focus:ring-2 focus:ring-[#174143]/20 rounded-lg"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label htmlFor="product_name" className="text-slate-700 font-semibold">Product Name</Label>
                            <Input
                              id="product_name"
                              name="product_name"
                              value={form.product_name}
                              onChange={onChange}
                              placeholder="e.g., iPhone 15"
                              required
                              className="h-12 border-2 border-slate-300 focus:border-[#174143] focus:ring-2 focus:ring-[#174143]/20 rounded-lg"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label htmlFor="quantity" className="text-slate-700 font-semibold">Quantity</Label>
                            <Input
                              id="quantity"
                              name="quantity"
                              type="number"
                              min="1"
                              value={form.quantity}
                              onChange={onChange}
                              required
                              className="h-12 border-2 border-slate-300 focus:border-[#174143] focus:ring-2 focus:ring-[#174143]/20 rounded-lg"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label htmlFor="budget" className="text-slate-700 font-semibold">Budget (PKR)</Label>
                            <Input
                              id="budget"
                              name="budget"
                              value={form.budget}
                              onChange={onChange}
                              placeholder="e.g., 285000"
                              required
                              className="h-12 border-2 border-slate-300 focus:border-[#174143] focus:ring-2 focus:ring-[#174143]/20 rounded-lg"
                            />
                          </div>
                        </div>
                      </div>

                      {/* Delivery Information */}
                      <div className="space-y-4">
                        <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                          <MapPin className="w-5 h-5 text-[#427A76]" />
                          Delivery Information
                        </h3>
                        <div className="space-y-2">
                          <Label htmlFor="delivery_address" className="text-slate-700 font-semibold">Delivery Address</Label>
                          <Textarea
                            id="delivery_address"
                            name="delivery_address"
                            value={form.delivery_address}
                            onChange={onChange}
                            placeholder="Enter complete delivery address"
                            rows={3}
                            required
                            className="border-2 border-slate-300 focus:border-[#174143] focus:ring-2 focus:ring-[#174143]/20 rounded-lg resize-none"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="notes" className="text-slate-700 font-semibold">Additional Notes (Optional)</Label>
                          <Textarea
                            id="notes"
                            name="notes"
                            value={form.notes}
                            onChange={onChange}
                            placeholder="Any special instructions or notes"
                            rows={2}
                            className="border-2 border-slate-300 focus:border-[#174143] focus:ring-2 focus:ring-[#174143]/20 rounded-lg resize-none"
                          />
                        </div>
                      </div>

                      {/* Status Message */}
                      {status && (
                        <motion.div
                          initial={{ opacity: 0, y: -10 }}
                          animate={{ opacity: 1, y: 0 }}
                          className={`p-4 rounded-lg flex items-start gap-3 ${
                            success ? "bg-green-50 border border-green-200" : "bg-red-50 border border-red-200"
                          }`}
                        >
                          {success ? (
                            <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                          ) : (
                            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                          )}
                          <p className={success ? "text-green-800" : "text-red-800"}>{status}</p>
                        </motion.div>
                      )}

                      {/* Submit Button */}
                      <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} className="pt-2">
                        <Button
                          type="submit"
                          disabled={loading}
                          className="w-full h-14 text-lg font-bold bg-gradient-to-r from-[#174143] to-[#427A76] hover:from-[#427A76] hover:to-[#174143] text-white shadow-2xl hover:shadow-3xl transition-all rounded-xl"
                        >
                          {loading ? (
                            <>
                              <Loader2 className="mr-2 h-6 w-6 animate-spin" />
                              Processing Order...
                            </>
                          ) : (
                            <>
                              <ShoppingCart className="mr-2 h-6 w-6" />
                              Create Order
                            </>
                          )}
                        </Button>
                      </motion.div>
                    </form>
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Right Side - Info & Images (20%) */}
            <div className="lg:col-span-1">
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 }}
                className="space-y-6 sticky top-24"
              >
                {/* AI Agent Info */}
                <Card className="border-0 shadow-lg bg-gradient-to-br from-[#174143] to-[#427A76] text-white">
                  <CardContent className="p-6 space-y-4">
                    <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                      <Sparkles className="w-6 h-6" />
                    </div>
                    <h3 className="text-lg font-bold">AI Agent Active</h3>
                    <p className="text-sm text-white/90">
                      Our Sales Agent will process this order automatically
                    </p>
                  </CardContent>
                </Card>

                {/* Features */}
                <Card className="border-0 shadow-lg">
                  <CardContent className="p-6 space-y-4">
                    <h3 className="font-bold text-slate-900">What Happens Next?</h3>
                    <div className="space-y-3">
                      {[
                        { icon: MessageSquare, text: "AI confirms order details" },
                        { icon: DollarSign, text: "Payment verification" },
                        { icon: Package, text: "Inventory auto-updates" },
                        { icon: FileText, text: "Receipt generated" },
                      ].map((item, i) => (
                        <div key={i} className="flex items-center gap-3 text-sm text-slate-600">
                          <div className="w-8 h-8 bg-[#174143]/10 rounded-lg flex items-center justify-center flex-shrink-0">
                            <item.icon className="w-4 h-4 text-[#174143]" />
                          </div>
                          {item.text}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Demo Image Placeholder */}
                <Card className="border-0 shadow-lg overflow-hidden">
                  <div className="aspect-square bg-gradient-to-br from-slate-100 to-slate-200 flex items-center justify-center">
                    <div className="text-center p-6">
                      <div className="text-5xl mb-3">📱</div>
                      <p className="text-sm text-slate-600 font-medium">WhatsApp Integration</p>
                    </div>
                  </div>
                </Card>
              </motion.div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

