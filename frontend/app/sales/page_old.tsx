"use client";

import { useState } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ShoppingCart, User, Phone, Package, DollarSign, MapPin, FileText, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";

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
      } else {
        setStatus("Unexpected response: " + res.status);
      }
    } catch (err: unknown) {
      // extract message safely from unknown error
      const getMsg = (e: unknown) => {
        if (typeof e === "object" && e !== null) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
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
    <div className="min-h-screen py-20 px-4 bg-gradient-to-br from-[rgb(var(--muted))] via-white to-[rgb(var(--muted))]">
      <div className="container mx-auto max-w-4xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          {/* Header */}
          <div className="text-center mb-8">
            <Badge className="mb-4 px-4 py-1.5 bg-[#427A76] text-white border-[#427A76]">
              <ShoppingCart className="w-3 h-3 mr-1" />
              Sales Order
            </Badge>
            <h1 className="text-4xl md:text-5xl font-bold mb-4 text-[#174143]">Create New Order</h1>
            <p className="text-lg text-[#427A76]">
              Fill in the details below to create a new sales order
            </p>
          </div>

          <Card className="border-2 shadow-xl bg-white backdrop-blur-sm border-[#427A76]/20">
            <CardHeader className="bg-white border-b border-[#427A76]/20">
              <CardTitle className="flex items-center gap-2 text-[#174143]">
                <Package className="w-5 h-5" />
                Order Details
              </CardTitle>
              <CardDescription className="text-[#427A76]">
                Enter customer and product information
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              <form onSubmit={onSubmit} className="space-y-6">
                {/* Customer Information */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold flex items-center gap-2 text-primary">
                    <User className="w-5 h-5" />
                    Customer Information
                  </h3>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="customer_name" className="flex items-center gap-2">
                        <User className="w-4 h-4 text-muted-foreground" />
                        Customer Name *
                      </Label>
                      <Input
                        id="customer_name"
                        name="customer_name"
                        value={form.customer_name}
                        onChange={onChange}
                        placeholder="Enter customer name"
                        required
                        className="border-primary/20 focus:border-primary"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="customer_phone" className="flex items-center gap-2">
                        <Phone className="w-4 h-4 text-muted-foreground" />
                        Phone Number *
                      </Label>
                      <Input
                        id="customer_phone"
                        name="customer_phone"
                        value={form.customer_phone}
                        onChange={onChange}
                        placeholder="+92 300 1234567"
                        required
                        className="border-primary/20 focus:border-primary"
                      />
                    </div>
                  </div>
                </div>

                {/* Product Information */}
                <div className="space-y-4 pt-4 border-t">
                  <h3 className="text-lg font-semibold flex items-center gap-2 text-primary">
                    <Package className="w-5 h-5" />
                    Product Information
                  </h3>
                  <div className="grid md:grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="product_id">Product ID *</Label>
                      <Input
                        id="product_id"
                        name="product_id"
                        value={form.product_id}
                        onChange={onChange}
                        placeholder="e.g., SKU-123"
                        required
                        className="border-primary/20 focus:border-primary"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="product_name">Product Name</Label>
                      <Input
                        id="product_name"
                        name="product_name"
                        value={form.product_name}
                        onChange={onChange}
                        placeholder="e.g., iPhone Charger"
                        className="border-primary/20 focus:border-primary"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="quantity">Quantity *</Label>
                      <Input
                        id="quantity"
                        name="quantity"
                        type="number"
                        min={1}
                        value={form.quantity}
                        onChange={onChange}
                        required
                        className="border-primary/20 focus:border-primary"
                      />
                    </div>
                  </div>
                </div>

                {/* Payment & Delivery */}
                <div className="space-y-4 pt-4 border-t">
                  <h3 className="text-lg font-semibold flex items-center gap-2 text-primary">
                    <DollarSign className="w-5 h-5" />
                    Payment & Delivery
                  </h3>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="budget" className="flex items-center gap-2">
                        <DollarSign className="w-4 h-4 text-muted-foreground" />
                        Budget (PKR)
                      </Label>
                      <Input
                        id="budget"
                        name="budget"
                        value={form.budget}
                        onChange={onChange}
                        placeholder="e.g., 5000"
                        className="border-primary/20 focus:border-primary"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="delivery_address" className="flex items-center gap-2">
                        <MapPin className="w-4 h-4 text-muted-foreground" />
                        Delivery Address
                      </Label>
                      <Input
                        id="delivery_address"
                        name="delivery_address"
                        value={form.delivery_address}
                        onChange={onChange}
                        placeholder="Enter delivery address"
                        className="border-primary/20 focus:border-primary"
                      />
                    </div>
                  </div>
                </div>

                {/* Notes */}
                <div className="space-y-2 pt-4 border-t">
                  <Label htmlFor="notes" className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-muted-foreground" />
                    Additional Notes
                  </Label>
                  <Textarea
                    id="notes"
                    name="notes"
                    value={form.notes}
                    onChange={onChange}
                    placeholder="Any special instructions or notes..."
                    rows={4}
                    className="border-primary/20 focus:border-primary resize-none"
                  />
                </div>

                {/* Status Message */}
                {status && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`p-4 rounded-lg flex items-center gap-3 ${
                      success
                        ? "bg-green-500/10 border border-green-500/20 text-green-700 dark:text-green-400"
                        : "bg-red-500/10 border border-red-500/20 text-red-700 dark:text-red-400"
                    }`}
                  >
                    {success ? (
                      <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
                    ) : (
                      <AlertCircle className="w-5 h-5 flex-shrink-0" />
                    )}
                    <p className="text-sm font-medium">{status}</p>
                  </motion.div>
                )}

                {/* Submit Button */}
                <div className="flex gap-4 pt-4">
                  <Button
                    type="submit"
                    disabled={loading}
                    size="lg"
                    className="flex-1 bg-[#174143] text-white hover:bg-[#427A76]"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        <ShoppingCart className="w-4 h-4 mr-2" />
                        Submit Order
                      </>
                    )}
                  </Button>
                    <Button
                    type="button"
                    variant="outline"
                    size="lg"
                    className="border-[#427A76] text-[#427A76] hover:bg-[rgb(var(--muted))]"
                    onClick={() => {
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
                      setStatus(null);
                      setSuccess(false);
                    }}
                  >
                    Reset
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
