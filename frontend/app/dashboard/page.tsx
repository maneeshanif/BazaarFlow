"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  TrendingUp,
  Package,
  DollarSign,
  Users,
  ShoppingCart,
  AlertCircle,
  CheckCircle2,
  Clock,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  MessageSquare,
  Megaphone,
} from "lucide-react";

const fadeInUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5 },
};

export default function DashboardPage() {
  const stats = [
    {
      title: "Total Revenue",
      value: "PKR 245,000",
      change: "+12.5%",
      trend: "up",
      icon: DollarSign,
      color: "from-green-600 to-emerald-600",
      bg: "bg-green-50",
      border: "border-green-200",
    },
    {
      title: "Orders Today",
      value: "48",
      change: "+8.2%",
      trend: "up",
      icon: ShoppingCart,
      color: "from-blue-600 to-cyan-600",
      bg: "bg-blue-50",
      border: "border-blue-200",
    },
    {
      title: "Active Products",
      value: "156",
      change: "-2.1%",
      trend: "down",
      icon: Package,
      color: "from-orange-600 to-orange-700",
      bg: "bg-orange-50",
      border: "border-orange-200",
    },
    {
      title: "Total Customers",
      value: "1,234",
      change: "+15.3%",
      trend: "up",
      icon: Users,
      color: "from-purple-600 to-indigo-600",
      bg: "bg-purple-50",
      border: "border-purple-200",
    },
  ];

  const recentOrders = [
    { id: "#ORD-001", customer: "Ahmed Khan", amount: "PKR 2,400", status: "completed", time: "2 mins ago" },
    { id: "#ORD-002", customer: "Fatima Ali", amount: "PKR 3,200", status: "pending", time: "15 mins ago" },
    { id: "#ORD-003", customer: "Hassan Raza", amount: "PKR 1,800", status: "completed", time: "1 hour ago" },
    { id: "#ORD-004", customer: "Ayesha Malik", amount: "PKR 4,500", status: "processing", time: "2 hours ago" },
  ];

  const lowStockItems = [
    { name: "iPhone Charger", stock: 5, threshold: 10 },
    { name: "Phone Case", stock: 3, threshold: 15 },
    { name: "Screen Protector", stock: 8, threshold: 20 },
  ];

  return (
    <div className="min-h-screen bg-white dark:bg-slate-900 py-20 px-4">
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <motion.div {...fadeInUp} className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-slate-900 dark:text-white mb-2">Dashboard</h1>
              <p className="text-slate-600 dark:text-slate-400">Welcome back! Here's what's happening today.</p>
            </div>
            <Badge className="px-4 py-2 bg-teal-50 text-teal-700 border border-teal-200 rounded-full">
              <div className="w-2 h-2 bg-teal-500 rounded-full animate-pulse mr-2" />
              All Agents Active
            </Badge>
          </div>
        </motion.div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat, i) => {
            const Icon = stat.icon;
            const TrendIcon = stat.trend === "up" ? ArrowUpRight : ArrowDownRight;
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
              >
                <Card className={`border-2 ${stat.border} ${stat.bg} dark:bg-slate-800 dark:border-slate-700 shadow-sm rounded-2xl hover:shadow-lg transition-all`}>
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className={`w-12 h-12 bg-gradient-to-br ${stat.color} rounded-xl flex items-center justify-center shadow-sm`}>
                        <Icon className="w-6 h-6 text-white" />
                      </div>
                      <div className={`flex items-center gap-1 text-sm font-medium ${
                        stat.trend === "up" ? "text-green-600" : "text-red-600"
                      }`}>
                        <TrendIcon className="w-4 h-4" />
                        {stat.change}
                      </div>
                    </div>
                    <h3 className="text-sm text-slate-600 dark:text-slate-400 mb-1">{stat.title}</h3>
                    <p className="text-2xl font-bold text-slate-900 dark:text-white">{stat.value}</p>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* Recent Orders */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card className="border-2 border-slate-200 dark:border-slate-700 dark:bg-slate-800 shadow-sm rounded-2xl">
              <CardHeader className="border-b border-slate-200 dark:border-slate-700">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg font-semibold text-slate-900 dark:text-white">Recent Orders</CardTitle>
                  <Link href="/dashboard/orders">
                    <Button variant="ghost" size="sm" className="text-teal-600 hover:text-teal-700 hover:bg-teal-50">
                      View All →
                    </Button>
                  </Link>
                </div>
              </CardHeader>
              <CardContent className="p-6">
                <div className="space-y-4">
                  {recentOrders.map((order, i) => (
                    <div key={i} className="flex items-center justify-between p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gradient-to-br from-[#174143] to-[#427A76] rounded-lg flex items-center justify-center">
                          <ShoppingCart className="w-5 h-5 text-white" />
                        </div>
                        <div>
                          <p className="font-medium text-slate-900 dark:text-white">{order.id}</p>
                          <p className="text-sm text-slate-600 dark:text-slate-400">{order.customer}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-semibold text-slate-900 dark:text-white">{order.amount}</p>
                        <Badge
                          className={`text-xs ${
                            order.status === "completed"
                              ? "bg-green-100 text-green-700 border-green-200"
                              : order.status === "pending"
                              ? "bg-blue-100 text-blue-700 border-blue-200"
                              : "bg-orange-100 text-orange-700 border-orange-200"
                          }`}
                        >
                          {order.status === "completed" && <CheckCircle2 className="w-3 h-3 mr-1" />}
                          {order.status === "pending" && <Clock className="w-3 h-3 mr-1" />}
                          {order.status}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Low Stock Alerts */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card className="border-2 border-slate-200 dark:border-slate-700 dark:bg-slate-800 shadow-sm rounded-2xl">
              <CardHeader className="border-b border-slate-200 dark:border-slate-700">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-orange-600" />
                    Low Stock Alerts
                  </CardTitle>
                  <Badge className="bg-orange-100 text-orange-700 border-orange-200">
                    {lowStockItems.length} Items
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-6">
                <div className="space-y-4">
                  {lowStockItems.map((item, i) => (
                    <div key={i} className="p-4 rounded-lg border-2 border-orange-200 bg-orange-50 dark:bg-slate-700 dark:border-orange-900">
                      <div className="flex items-center justify-between mb-2">
                        <p className="font-medium text-slate-900 dark:text-white">{item.name}</p>
                        <Badge className="bg-orange-200 text-orange-800 border-orange-300">
                          {item.stock} left
                        </Badge>
                      </div>
                      <div className="w-full bg-orange-200 dark:bg-slate-600 rounded-full h-2">
                        <div
                          className="bg-gradient-to-r from-orange-600 to-orange-700 h-2 rounded-full"
                          style={{ width: `${(item.stock / item.threshold) * 100}%` }}
                        />
                      </div>
                      <p className="text-xs text-slate-600 dark:text-slate-400 mt-2">
                        Threshold: {item.threshold} units
                      </p>
                    </div>
                  ))}
                </div>
                <Button className="w-full mt-4 bg-gradient-to-r from-orange-600 to-orange-700 hover:from-orange-700 hover:to-orange-600 text-white rounded-xl">
                  <Package className="w-4 h-4 mr-2" />
                  Reorder All
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="mt-6"
        >
          <Card className="border-2 border-slate-200 dark:border-slate-700 dark:bg-slate-800 shadow-sm rounded-2xl">
            <CardHeader>
              <CardTitle className="text-lg font-semibold text-slate-900 dark:text-white">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <Link href="/chat/analytics">
                  <Button variant="outline" className="w-full h-20 flex-col gap-2 border-2 border-teal-200 hover:bg-teal-50 dark:border-teal-900 dark:hover:bg-teal-950">
                    <BarChart3 className="w-6 h-6 text-teal-600" />
                    <span className="text-sm">Analytics</span>
                  </Button>
                </Link>
                <Link href="/chat/inventory">
                  <Button variant="outline" className="w-full h-20 flex-col gap-2 border-2 border-orange-200 hover:bg-orange-50 dark:border-orange-900 dark:hover:bg-orange-950">
                    <Package className="w-6 h-6 text-orange-600" />
                    <span className="text-sm">Inventory</span>
                  </Button>
                </Link>
                <Link href="/chat/sales">
                  <Button variant="outline" className="w-full h-20 flex-col gap-2 border-2 border-blue-200 hover:bg-blue-50 dark:border-blue-900 dark:hover:bg-blue-950">
                    <MessageSquare className="w-6 h-6 text-blue-600" />
                    <span className="text-sm">Sales</span>
                  </Button>
                </Link>
                <Link href="/chat/finance">
                  <Button variant="outline" className="w-full h-20 flex-col gap-2 border-2 border-green-200 hover:bg-green-50 dark:border-green-900 dark:hover:bg-green-950">
                    <DollarSign className="w-6 h-6 text-green-600" />
                    <span className="text-sm">Finance</span>
                  </Button>
                </Link>
                <Link href="/chat/marketing">
                  <Button variant="outline" className="w-full h-20 flex-col gap-2 border-2 border-pink-200 hover:bg-pink-50 dark:border-pink-900 dark:hover:bg-pink-950">
                    <Megaphone className="w-6 h-6 text-pink-600" />
                    <span className="text-sm">Marketing</span>
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
