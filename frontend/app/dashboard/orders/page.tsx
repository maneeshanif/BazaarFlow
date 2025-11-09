"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  ShoppingCart,
  CheckCircle2,
  Clock,
  XCircle,
  Search,
  Filter,
  Download,
  ArrowLeft,
  Package,
  DollarSign,
  User,
  Calendar,
} from "lucide-react";

const allOrders = [
  {
    id: '#ORD-001',
    customer: 'Ahmed Khan',
    items: '2x iPhone Charger',
    amount: 'PKR 2,400',
    status: 'completed',
    date: '2024-01-15',
    time: '2 mins ago',
    paymentMethod: 'JazzCash'
  },
  {
    id: '#ORD-002',
    customer: 'Fatima Ali',
    items: '1x Phone Case, 1x Screen Protector',
    amount: 'PKR 3,200',
    status: 'pending',
    date: '2024-01-15',
    time: '15 mins ago',
    paymentMethod: 'Easypaisa'
  },
  {
    id: '#ORD-003',
    customer: 'Hassan Raza',
    items: '3x USB Cable',
    amount: 'PKR 1,800',
    status: 'completed',
    date: '2024-01-15',
    time: '1 hour ago',
    paymentMethod: 'Cash'
  },
  {
    id: '#ORD-004',
    customer: 'Ayesha Malik',
    items: '1x Power Bank',
    amount: 'PKR 4,500',
    status: 'processing',
    date: '2024-01-15',
    time: '2 hours ago',
    paymentMethod: 'JazzCash'
  },
  {
    id: '#ORD-005',
    customer: 'Bilal Ahmed',
    items: '2x Earphones',
    amount: 'PKR 2,800',
    status: 'completed',
    date: '2024-01-14',
    time: '1 day ago',
    paymentMethod: 'Easypaisa'
  },
  {
    id: '#ORD-006',
    customer: 'Zainab Khan',
    items: '1x Bluetooth Speaker',
    amount: 'PKR 5,200',
    status: 'cancelled',
    date: '2024-01-14',
    time: '1 day ago',
    paymentMethod: 'Cash'
  },
  {
    id: '#ORD-007',
    customer: 'Usman Ali',
    items: '4x Phone Case',
    amount: 'PKR 3,600',
    status: 'completed',
    date: '2024-01-14',
    time: '2 days ago',
    paymentMethod: 'JazzCash'
  },
  {
    id: '#ORD-008',
    customer: 'Sana Tariq',
    items: '1x Wireless Charger',
    amount: 'PKR 3,900',
    status: 'processing',
    date: '2024-01-13',
    time: '2 days ago',
    paymentMethod: 'Easypaisa'
  },
];

export default function OrdersPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");

  const filteredOrders = allOrders.filter(order => {
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
    { label: "Total Orders", value: allOrders.length, icon: ShoppingCart, color: "from-blue-600 to-cyan-600" },
    { label: "Completed", value: allOrders.filter(o => o.status === "completed").length, icon: CheckCircle2, color: "from-green-600 to-emerald-600" },
    { label: "Pending", value: allOrders.filter(o => o.status === "pending").length, icon: Clock, color: "from-orange-600 to-orange-700" },
    { label: "Processing", value: allOrders.filter(o => o.status === "processing").length, icon: Package, color: "from-purple-600 to-indigo-600" },
  ];

  return (
    <div className="min-h-screen bg-white dark:bg-slate-900 py-20 px-4">
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center gap-4 mb-4">
            <Link href="/dashboard">
              <Button variant="outline" size="sm" className="gap-2">
                <ArrowLeft className="w-4 h-4" />
                Back to Dashboard
              </Button>
            </Link>
          </div>
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
                        <Button variant="outline" size="sm" className="rounded-xl">
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
      </div>
    </div>
  );
}
