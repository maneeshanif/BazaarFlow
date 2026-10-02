"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import {
  ShoppingCart,
  CheckCircle2,
  Clock,
  XCircle,
  Search,
  Download,
  Package,
  DollarSign,
  User,
  Calendar,
  Loader2,
  Phone,
  MapPin,
  FileText,
} from "lucide-react";
import axios from "axios";
import { DashboardLayout } from "@/components/DashboardSidebar";
import { toast } from "sonner";

interface Order {
  id: number;
  customer_name: string;
  customer_phone: string;
  product_name: string;
  quantity: number;
  budget: string;
  payment_status: string;
  delivery_address: string;
  notes: string;
}

interface FormattedOrder {
  id: string;
  customer: string;
  phone: string;
  items: string;
  amount: string;
  amountNum: number;
  status: string;
  date: string;
  time: string;
  paymentMethod: string;
  address: string;
  notes: string;
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [selectedOrder, setSelectedOrder] = useState<FormattedOrder | null>(null);

  useEffect(() => {
    fetchOrders();
  }, []);

  const fetchOrders = async () => {
    try {
      const response = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/api/sales`);
      if (response.data.ok) {
        setOrders(response.data.orders || []);
      }
    } catch (error) {
      console.error("Failed to fetch orders:", error);
    } finally {
      setLoading(false);
    }
  };

  const formattedOrders: FormattedOrder[] = orders.map((order) => {
    const budgetStr = order.budget?.replace(/,/g, "").trim() || "0";
    const budget = parseInt(budgetStr, 10) || 0;
    const quantity = parseInt(String(order.quantity), 10) || 1;
    const totalAmount = budget * quantity;

    return {
      id: `#ORD-${order.id.toString().padStart(3, '0')}`,
      customer: order.customer_name,
      phone: order.customer_phone,
      items: `${quantity}x ${order.product_name}`,
      amount: `PKR ${totalAmount.toLocaleString()}`,
      amountNum: totalAmount,
      status: order.payment_status || "pending",
      date: new Date().toISOString().split('T')[0],
      time: "Recently",
      paymentMethod: "Pending",
      address: order.delivery_address,
      notes: order.notes,
    };
  });

  const filteredOrders = formattedOrders.filter(order => {
    const matchesSearch = order.customer.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         order.id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = filterStatus === "all" || order.status === filterStatus;
    return matchesSearch && matchesFilter;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-700 border-green-200";
      case "pending":
        return "bg-blue-100 text-blue-700 border-blue-200";
      case "processing":
        return "bg-orange-100 text-orange-700 border-orange-200";
      case "cancelled":
        return "bg-red-100 text-red-700 border-red-200";
      default:
        return "bg-slate-100 text-slate-700 border-slate-200";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="w-4 h-4" />;
      case "pending":
        return <Clock className="w-4 h-4" />;
      case "processing":
        return <Package className="w-4 h-4" />;
      case "cancelled":
        return <XCircle className="w-4 h-4" />;
      default:
        return null;
    }
  };

  const stats = [
    { label: "Total Orders", value: formattedOrders.length, icon: ShoppingCart, color: "from-blue-600 to-cyan-600" },
    { label: "Completed", value: formattedOrders.filter(o => o.status === "completed" || o.status === "paid").length, icon: CheckCircle2, color: "from-green-600 to-emerald-600" },
    { label: "Pending", value: formattedOrders.filter(o => o.status === "pending").length, icon: Clock, color: "from-orange-600 to-orange-700" },
    { label: "Processing", value: formattedOrders.filter(o => o.status === "processing").length, icon: Package, color: "from-purple-600 to-indigo-600" },
  ];

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-96">
          <Loader2 className="w-8 h-8 animate-spin text-[#174143]" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-4xl font-bold text-slate-900 dark:text-white mb-2">All Orders</h1>
          <p className="text-slate-600 dark:text-slate-400">Manage and track all your orders</p>
        </motion.div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {stats.map((stat, i) => {
            const Icon = stat.icon;
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
              >
                <Card className="border-2 border-slate-200 dark:border-slate-700 dark:bg-slate-800 shadow-sm rounded-2xl">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 bg-gradient-to-br ${stat.color} rounded-lg flex items-center justify-center shadow-sm`}>
                        <Icon className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <p className="text-xs text-slate-600 dark:text-slate-400">{stat.label}</p>
                        <p className="text-2xl font-bold text-slate-900 dark:text-white">{stat.value}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </div>

        {/* Search and Filter */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mb-6"
        >
          <Card className="border-2 border-slate-200 dark:border-slate-700 dark:bg-slate-800 shadow-sm rounded-2xl">
            <CardContent className="p-6">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <Input
                    placeholder="Search by order ID or customer name..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10 h-12 border-2 border-slate-200 dark:border-slate-600 rounded-xl"
                  />
                </div>
                <div className="flex gap-2">
                  <Button
                    variant={filterStatus === "all" ? "default" : "outline"}
                    onClick={() => setFilterStatus("all")}
                    className="rounded-xl"
                  >
                    All
                  </Button>
                  <Button
                    variant={filterStatus === "completed" ? "default" : "outline"}
                    onClick={() => setFilterStatus("completed")}
                    className="rounded-xl"
                  >
                    Completed
                  </Button>
                  <Button
                    variant={filterStatus === "pending" ? "default" : "outline"}
                    onClick={() => setFilterStatus("pending")}
                    className="rounded-xl"
                  >
                    Pending
                  </Button>
                  <Button variant="outline" className="gap-2 rounded-xl">
                    <Download className="w-4 h-4" />
                    Export
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Orders List */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card className="border-2 border-slate-200 dark:border-slate-700 dark:bg-slate-800 shadow-sm rounded-2xl">
            <CardHeader className="border-b border-slate-200 dark:border-slate-700">
              <CardTitle className="text-lg font-semibold text-slate-900 dark:text-white">
                Orders ({filteredOrders.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-slate-200 dark:divide-slate-700">
                {filteredOrders.map((order, i) => (
                  <motion.div
                    key={order.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="p-6 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                  >
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div className="flex items-start gap-4">
                        <div className="w-12 h-12 bg-gradient-to-br from-[#174143] to-[#427A76] rounded-xl flex items-center justify-center flex-shrink-0">
                          <ShoppingCart className="w-6 h-6 text-white" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="font-semibold text-slate-900 dark:text-white">{order.id}</h3>
                            <Badge className={`${getStatusColor(order.status)} flex items-center gap-1`}>
                              {getStatusIcon(order.status)}
                              {order.status}
                            </Badge>
                          </div>
                          <div className="space-y-1 text-sm text-slate-600 dark:text-slate-400">
                            <div className="flex items-center gap-2">
                              <User className="w-4 h-4" />
                              <span>{order.customer}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <Package className="w-4 h-4" />
                              <span>{order.items}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <Calendar className="w-4 h-4" />
                              <span>{order.time}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="text-sm text-slate-600 dark:text-slate-400 mb-1">Amount</p>
                          <p className="text-xl font-bold text-slate-900 dark:text-white">{order.amount}</p>
                          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{order.paymentMethod}</p>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          className="rounded-xl"
                          onClick={() => setSelectedOrder(order)}
                        >
                          View Details
                        </Button>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Order Details Modal */}
        <Dialog open={!!selectedOrder} onOpenChange={(open) => !open && setSelectedOrder(null)}>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            {selectedOrder && (
              <>
                <DialogHeader className="space-y-3">
                  <div className="flex items-center gap-4">
                    <div className="w-16 h-16 bg-gradient-to-br from-[#174143] to-[#427A76] rounded-2xl flex items-center justify-center shadow-lg">
                      <ShoppingCart className="w-8 h-8 text-white" />
                    </div>
                    <div className="flex-1">
                      <DialogTitle className="text-2xl font-bold text-slate-900 dark:text-white">
                        {selectedOrder.id}
                      </DialogTitle>
                      <DialogDescription className="text-slate-600 dark:text-slate-400">
                        Order placed {selectedOrder.time}
                      </DialogDescription>
                    </div>
                    <Badge className={`${getStatusColor(selectedOrder.status)} flex items-center gap-2 text-base px-4 py-2 shadow-sm`}>
                      {getStatusIcon(selectedOrder.status)}
                      {selectedOrder.status.toUpperCase()}
                    </Badge>
                  </div>
                </DialogHeader>

                <Separator className="my-4" />

                <div className="space-y-6">
                  {/* Customer Information */}
                  <div className="bg-gradient-to-br from-blue-50 to-cyan-50 dark:from-slate-800 dark:to-slate-700 rounded-2xl p-5 border-2 border-blue-100 dark:border-slate-600">
                    <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2 text-lg">
                      <User className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                      Customer Information
                    </h3>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center bg-white/60 dark:bg-slate-900/40 rounded-lg p-3">
                        <span className="text-slate-600 dark:text-slate-400 font-medium">Name</span>
                        <span className="font-semibold text-slate-900 dark:text-white">{selectedOrder.customer}</span>
                      </div>
                      <div className="flex justify-between items-center bg-white/60 dark:bg-slate-900/40 rounded-lg p-3">
                        <span className="text-slate-600 dark:text-slate-400 font-medium">Phone</span>
                        <span className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                          <Phone className="w-4 h-4 text-green-600" />
                          {selectedOrder.phone}
                        </span>
                      </div>
                      <div className="flex justify-between items-start bg-white/60 dark:bg-slate-900/40 rounded-lg p-3">
                        <span className="text-slate-600 dark:text-slate-400 font-medium">Address</span>
                        <span className="font-semibold text-slate-900 dark:text-white text-right max-w-xs flex items-start gap-2">
                          <MapPin className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
                          {selectedOrder.address || "Not provided"}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Order Items */}
                  <div className="bg-gradient-to-br from-purple-50 to-pink-50 dark:from-slate-800 dark:to-slate-700 rounded-2xl p-5 border-2 border-purple-100 dark:border-slate-600">
                    <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2 text-lg">
                      <Package className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                      Order Items
                    </h3>
                    <div className="bg-white/60 dark:bg-slate-900/40 rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-slate-900 dark:text-white">{selectedOrder.items}</span>
                        <Badge variant="outline" className="text-purple-700 dark:text-purple-300 border-purple-300">
                          In Stock
                        </Badge>
                      </div>
                    </div>
                  </div>

                  {/* Payment Information */}
                  <div className="bg-gradient-to-br from-green-50 to-emerald-50 dark:from-slate-800 dark:to-slate-700 rounded-2xl p-5 border-2 border-green-100 dark:border-slate-600">
                    <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2 text-lg">
                      <DollarSign className="w-5 h-5 text-green-600 dark:text-green-400" />
                      Payment Information
                    </h3>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center bg-white/60 dark:bg-slate-900/40 rounded-lg p-4">
                        <span className="text-slate-600 dark:text-slate-400 font-medium">Total Amount</span>
                        <span className="text-3xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
                          {selectedOrder.amount}
                        </span>
                      </div>
                      <div className="flex justify-between items-center bg-white/60 dark:bg-slate-900/40 rounded-lg p-3">
                        <span className="text-slate-600 dark:text-slate-400 font-medium">Payment Method</span>
                        <span className="font-semibold text-slate-900 dark:text-white">{selectedOrder.paymentMethod}</span>
                      </div>
                      <div className="flex justify-between items-center bg-white/60 dark:bg-slate-900/40 rounded-lg p-3">
                        <span className="text-slate-600 dark:text-slate-400 font-medium">Order Date</span>
                        <span className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                          <Calendar className="w-4 h-4 text-blue-600" />
                          {selectedOrder.date}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Notes */}
                  {selectedOrder.notes && (
                    <div className="bg-gradient-to-br from-amber-50 to-orange-50 dark:from-slate-800 dark:to-slate-700 rounded-2xl p-5 border-2 border-amber-100 dark:border-slate-600">
                      <h3 className="font-semibold text-slate-900 dark:text-white mb-3 flex items-center gap-2 text-lg">
                        <FileText className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                        Order Notes
                      </h3>
                      <p className="text-sm text-slate-700 dark:text-slate-300 bg-white/60 dark:bg-slate-900/40 rounded-lg p-4 leading-relaxed">
                        {selectedOrder.notes}
                      </p>
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div className="flex gap-3 pt-4">
                    <Button 
                      className="flex-1 h-12 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white shadow-lg hover:shadow-xl transition-all"
                      onClick={() => {
                        toast.success("Order Completed!", {
                          description: `Order ${selectedOrder.id} has been marked as completed.`,
                        });
                        setSelectedOrder(null);
                      }}
                    >
                      <CheckCircle2 className="w-5 h-5 mr-2" />
                      Mark as Completed
                    </Button>
                    <Button 
                      variant="outline" 
                      className="flex-1 h-12 border-2 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all"
                      onClick={() => {
                        toast.info("Printing Invoice...", {
                          description: "Invoice is being prepared for printing.",
                        });
                      }}
                    >
                      <Download className="w-5 h-5 mr-2" />
                      Print Invoice
                    </Button>
                  </div>
                </div>
              </>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  );
}
