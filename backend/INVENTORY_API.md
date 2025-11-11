# Inventory Management API

## Overview
Complete CRUD API for managing inventory items with stock tracking and supplier management.

## Endpoints

### 1. Get All Inventory Items
```
GET /api/inventory
```
**Response:**
```json
{
  "ok": true,
  "items": [
    {
      "sku": "TECH-001",
      "name": "Product Name",
      "category": "Electronics",
      "price": 5000,
      "stock": 150,
      "reorder_point": 20,
      "incoming": 50,
      "supplier": "Tech Suppliers Ltd",
      "last_restocked": "2025-01-10"
    }
  ]
}
```

### 2. Get Single Item by SKU
```
GET /api/inventory/{sku}
```
**Response:**
```json
{
  "ok": true,
  "item": { ... }
}
```

### 3. Create New Item
```
POST /api/inventory
```
**Request Body:**
```json
{
  "sku": "NEW-SKU",
  "name": "New Product",
  "category": "Category",
  "price": 1000,
  "stock": 50,
  "reorder_point": 10,
  "incoming": 0,
  "supplier": "Supplier Name"
}
```
**Response:**
```json
{
  "ok": true,
  "item": { ... },
  "message": "Item created successfully"
}
```

### 4. Update Item
```
PUT /api/inventory/{sku}
```
**Request Body:** (all fields optional)
```json
{
  "name": "Updated Name",
  "price": 1200,
  "stock": 60
}
```
**Response:**
```json
{
  "ok": true,
  "item": { ... },
  "message": "Item updated successfully"
}
```

### 5. Add Stock
```
PATCH /api/inventory/{sku}/add-stock
```
**Request Body:**
```json
{
  "quantity": 50
}
```
**Response:**
```json
{
  "ok": true,
  "item": { ... },
  "message": "Added 50 units to stock"
}
```

## Features
- ✅ Full CRUD operations
- ✅ SKU-based item identification
- ✅ Stock level tracking
- ✅ Automatic timestamp on stock updates
- ✅ Low stock detection (stock <= reorder_point)
- ✅ Incoming stock tracking
- ✅ Supplier management
- ✅ Validation (unique SKU, positive quantities)
- ✅ Error handling with proper HTTP status codes

## Frontend Integration
The inventory page (`frontend/app/dashboard/inventory/page.tsx`) is fully integrated with:
- Dialog forms for add/edit operations
- Real-time stock additions with toast notifications
- Stats cards showing total items, low stock count, and total value
- Responsive design with shadcn/ui components

## Data Storage
All inventory data is persisted to `backend/data/inventory_items.json` with automatic caching for performance.
