"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Package,
  Plus,
  Edit,
  Loader2,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Box,
} from "lucide-react";
import axios from "axios";
import { DashboardLayout } from "@/components/DashboardSidebar";
import { toast } from "sonner";

interface InventoryItem {
  sku: string;
  name: string;
  category: string;
  price: number;
  stock: number;
  reorder_point: number;
  incoming: number;
  supplier: string;
  last_restocked: string;
}

export default function InventoryPage() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<InventoryItem | null>(null);
  const [formData, setFormData] = useState<Partial<InventoryItem>>({
    sku: "",
    name: "",
    category: "",
    price: 0,
    stock: 0,
    reorder_point: 0,
    incoming: 0,
    supplier: "",
  });

  useEffect(() => {
    fetchInventory();
  }, []);

  const fetchInventory = async () => {
    try {
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/api/inventory`
      );
      if (response.data.items) {
        setItems(response.data.items);
      }
    } catch (error) {
      console.error("Failed to fetch inventory:", error);
      toast.error("Failed to load inventory");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const endpoint = editingItem
        ? `${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/api/inventory/${formData.sku}`
        : `${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/api/inventory`;
      
      const method = editingItem ? "put" : "post";
      
      await axios[method](endpoint, formData);
      
      toast.success(editingItem ? "Item updated successfully!" : "Item added successfully!");
      setDialogOpen(false);
      resetForm();
      fetchInventory();
    } catch (error) {
      console.error("Failed to save item:", error);
      toast.error("Failed to save item");
    }
  };

  const resetForm = () => {
    setFormData({
      sku: "",
      name: "",
      category: "",
      price: 0,
      stock: 0,
      reorder_point: 0,
      incoming: 0,
      supplier: "",
    });
    setEditingItem(null);
  };

  const handleEdit = (item: InventoryItem) => {
    setEditingItem(item);
    setFormData(item);
    setDialogOpen(true);
  };

  const handleAddStock = async (sku: string, additionalStock: number) => {
    try {
      await axios.patch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/api/inventory/${sku}/add-stock`,
        { quantity: additionalStock }
      );
      toast.success(`Added ${additionalStock} units to stock!`);
      fetchInventory();
    } catch (error) {
      console.error("Failed to add stock:", error);
      toast.error("Failed to update stock");
    }
  };

  const lowStockItems = items.filter((item) => item.stock <= item.reorder_point);
  const totalValue = items.reduce((sum, item) => sum + item.price * item.stock, 0);

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
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-slate-900 dark:text-white mb-2">
                Inventory Management
              </h1>
              <p className="text-slate-600 dark:text-slate-400">
                Manage products, stock levels, and suppliers
              </p>
            </div>
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button
                  className="bg-gradient-to-r from-[#174143] to-[#427A76] hover:from-[#427A76] hover:to-[#174143]"
                  onClick={resetForm}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add New Item
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[600px]">
                <DialogHeader>
                  <DialogTitle>
                    {editingItem ? "Edit Item" : "Add New Item"}
                  </DialogTitle>
                  <DialogDescription>
                    {editingItem
                      ? "Update the details of the inventory item"
                      : "Add a new product to your inventory"}
                  </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleSubmit}>
                  <div className="grid grid-cols-2 gap-4 py-4">
                    <div className="space-y-2">
                      <Label htmlFor="sku">SKU</Label>
                      <Input
                        id="sku"
                        value={formData.sku}
                        onChange={(e) =>
                          setFormData({ ...formData, sku: e.target.value })
                        }
                        disabled={!!editingItem}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="name">Product Name</Label>
                      <Input
                        id="name"
                        value={formData.name}
                        onChange={(e) =>
                          setFormData({ ...formData, name: e.target.value })
                        }
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="category">Category</Label>
                      <Input
                        id="category"
                        value={formData.category}
                        onChange={(e) =>
                          setFormData({ ...formData, category: e.target.value })
                        }
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="price">Price (PKR)</Label>
                      <Input
                        id="price"
                        type="number"
                        value={formData.price}
                        onChange={(e) =>
                          setFormData({ ...formData, price: Number(e.target.value) })
                        }
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="stock">Stock</Label>
                      <Input
                        id="stock"
                        type="number"
                        value={formData.stock}
                        onChange={(e) =>
                          setFormData({ ...formData, stock: Number(e.target.value) })
                        }
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="reorder_point">Reorder Point</Label>
                      <Input
                        id="reorder_point"
                        type="number"
                        value={formData.reorder_point}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            reorder_point: Number(e.target.value),
                          })
                        }
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="incoming">Incoming Stock</Label>
                      <Input
                        id="incoming"
                        type="number"
                        value={formData.incoming}
                        onChange={(e) =>
                          setFormData({ ...formData, incoming: Number(e.target.value) })
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="supplier">Supplier</Label>
                      <Input
                        id="supplier"
                        value={formData.supplier}
                        onChange={(e) =>
                          setFormData({ ...formData, supplier: e.target.value })
                        }
                        required
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button type="submit" className="bg-gradient-to-r from-[#174143] to-[#427A76]">
                      {editingItem ? "Update Item" : "Add Item"}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        </motion.div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Card className="border-2 border-slate-200 dark:border-slate-700 dark:bg-slate-800">
              <CardContent className="p-6">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-cyan-600 rounded-lg flex items-center justify-center">
                    <Package className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <p className="text-sm text-slate-600 dark:text-slate-400">Total Items</p>
                    <p className="text-2xl font-bold text-slate-900 dark:text-white">{items.length}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card className="border-2 border-slate-200 dark:border-slate-700 dark:bg-slate-800">
              <CardContent className="p-6">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-red-600 to-orange-600 rounded-lg flex items-center justify-center">
                    <AlertCircle className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <p className="text-sm text-slate-600 dark:text-slate-400">Low Stock</p>
                    <p className="text-2xl font-bold text-slate-900 dark:text-white">
                      {lowStockItems.length}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card className="border-2 border-slate-200 dark:border-slate-700 dark:bg-slate-800">
              <CardContent className="p-6">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-green-600 to-emerald-600 rounded-lg flex items-center justify-center">
                    <Box className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <p className="text-sm text-slate-600 dark:text-slate-400">Total Value</p>
                    <p className="text-2xl font-bold text-slate-900 dark:text-white">
                      PKR {totalValue.toLocaleString()}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Inventory Grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card className="border-2 border-slate-200 dark:border-slate-700 dark:bg-slate-800">
            <CardHeader>
              <CardTitle>Inventory Items ({items.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {items.map((item, i) => (
                  <motion.div
                    key={item.sku}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="p-4 bg-slate-50 dark:bg-slate-700 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-600 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4 flex-1">
                        <div className="w-12 h-12 bg-gradient-to-br from-[#174143] to-[#427A76] rounded-lg flex items-center justify-center">
                          <Package className="w-6 h-6 text-white" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-1">
                            <h3 className="font-semibold text-slate-900 dark:text-white">
                              {item.name}
                            </h3>
                            <Badge variant="outline" className="text-xs">
                              {item.category}
                            </Badge>
                            {item.stock <= item.reorder_point && (
                              <Badge className="bg-red-100 text-red-700 border-red-200">
                                <AlertCircle className="w-3 h-3 mr-1" />
                                Low Stock
                              </Badge>
                            )}
                          </div>
                          <div className="flex items-center gap-4 text-sm text-slate-600 dark:text-slate-400">
                            <span>SKU: {item.sku}</span>
                            <span>Stock: {item.stock}</span>
                            <span>Price: PKR {item.price.toLocaleString()}</span>
                            <span>Supplier: {item.supplier}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            const quantity = window.prompt("Add stock quantity:", "10");
                            if (quantity) {
                              handleAddStock(item.sku, parseInt(quantity));
                            }
                          }}
                        >
                          <TrendingUp className="w-4 h-4 mr-1" />
                          Add Stock
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEdit(item)}
                        >
                          <Edit className="w-4 h-4 mr-1" />
                          Edit
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
    </DashboardLayout>
  );
}
