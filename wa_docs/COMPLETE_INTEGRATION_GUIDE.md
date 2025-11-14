# BazaarFlow - Complete WhatsApp Agent Integration Guide

## 🎯 Overview

BazaarFlow is a multi-tenant WhatsApp sales agent system where:
- **Vendors** are businesses with their own WhatsApp Business numbers
- **Customers** are people who message the vendor's WhatsApp number
- **AI Agent** automatically responds to customer messages using OpenAI Agents SDK
- **Dashboard** shows all customers and conversation history in real-time

## 📋 Current Setup Status

### ✅ What's Working

1. **Vendor Management**
   - Vendor created and stored: `d2f0e426-b0ee-4590-88d0-663133267a98`
   - WhatsApp credentials saved (Phone Number ID, WABA ID, Access Token)
   - Credentials validated with Meta API

2. **Frontend Dashboard**
   - `/dashboard/sales/settings` - Save WhatsApp credentials
   - `/dashboard/sales/my-users` - View all customers who messaged
   - `/dashboard/sales/history` - View conversation history with each customer

3. **Backend API**
   - Webhook endpoint ready: `POST /webhook`
   - Customer listing: `GET /api/vendors/{vendor_id}/customers`
   - Message history: `GET /api/vendors/{vendor_id}/customers/{phone}/messages`

4. **AI Agent Integration**
   - Sales agent with finance and inventory capabilities
   - Agent runner enabled and ready
   - Conversation history tracking

## 🔄 How It Works - Complete Flow

### 1. Customer Sends Message to Your WhatsApp Business Number

```
Customer (923001234567) → WhatsApp Cloud API → Your Webhook
```

### 2. Webhook Receives and Processes Message

**File: `backend/webhook.py`**

```python
@router.post("/webhook")
async def inbound_webhook(request: Request):
    # Extracts message data
    # Creates/updates vendor (auto by phone_number_id)
    # Creates/updates customer (by phone number)
    # Records inbound message in database
    # Calls agent via runner_hook()
    # Sends agent's reply back to customer
    # Records outbound message in database
```

### 3. Agent Processes and Replies

**File: `backend/runner.py`**

The agent:
- Loads conversation history (last 10 messages)
- Analyzes customer intent
- Can check inventory, create orders, handle payments
- Generates intelligent reply (max 320 characters)
- Returns structured response

### 4. Frontend Auto-Updates

**Real-time Data Flow:**
```
New Message → Database Updated → Frontend Fetches → UI Shows Customer
```

- New customers appear in `/dashboard/sales/my-users`
- Conversation history updates in `/dashboard/sales/history`
- Status badges show activity (Active/Recent/Dormant)

## 🚀 Testing the Complete Flow

### Step 1: Start Backend Server

```bash
cd backend
source .venv/bin/activate
fastapi dev app.py
```

Server should start on `http://localhost:8000`

### Step 2: Start Frontend

```bash
cd frontend
npm run dev
```

Dashboard runs on `http://localhost:3000`

### Step 3: Test with Webhook Simulator

```bash
cd backend
python test_webhook_flow.py
```

This simulates a customer message and shows:
- ✅ Webhook received
- ✅ Customer created
- ✅ Message stored
- ✅ Agent replied
- ✅ Reply message stored

### Step 4: View in Dashboard

1. Open `http://localhost:3000/dashboard/sales/my-users`
2. You should see the test customer: `923001234567`
3. Click "View conversation"
4. See both inbound and outbound messages

### Step 5: Test with Real WhatsApp

1. Configure Meta App webhook URL to your server (use ngrok for local testing)
2. Send message from your phone to the business number
3. Watch agent auto-reply
4. Check dashboard for live updates

## 🗃️ Database Structure

### vendors.json
```json
{
  "vendor_id": "uuid",
  "name": "Business Name",
  "phone_number_id": "710222118850893",
  "waba_id": "1490360058646099", 
  "access_token": "EAAG...",
  "settings": {},
  "created_at": "ISO timestamp",
  "updated_at": "ISO timestamp"
}
```

### customers.json
```json
{
  "id": "uuid",
  "vendor_id": "vendor uuid",
  "phone": "923001234567",
  "name": "Customer Name",
  "first_seen": "ISO timestamp",
  "last_seen": "ISO timestamp"
}
```

### messages.json
```json
{
  "id": "uuid",
  "vendor_id": "vendor uuid",
  "customer_phone": "923001234567",
  "direction": "inbound|outbound",
  "text": "Message content",
  "raw_payload": {},
  "timestamp": "ISO timestamp"
}
```

## 🔧 Key Configuration

### Environment Variables (backend/.env)

```bash
# Meta WhatsApp
META_VERIFY_TOKEN=test123

# Optional
FRONTEND_ORIGIN=http://localhost:3000
OPENAI_API_KEY=your_key_here
```

### Meta Webhook Setup

1. Go to Meta App Dashboard
2. WhatsApp → Configuration → Webhook
3. Set Callback URL: `https://your-domain.com/webhook`
4. Set Verify Token: `test123` (same as META_VERIFY_TOKEN)
5. Subscribe to: `messages`

## 📱 Frontend Features

### Dashboard Routes

| Route | Purpose |
|-------|---------|
| `/dashboard/sales` | Overview |
| `/dashboard/sales/settings` | Configure WhatsApp credentials |
| `/dashboard/sales/my-users` | List all customers |
| `/dashboard/sales/history` | View conversations |

### Customer Status Badges

- **Active** (Green) - Messaged within last hour
- **Recent** (Blue) - Messaged within last 12 hours
- **Dormant** (Gray) - No recent activity

## 🤖 Agent Capabilities

The sales agent can:

1. **Answer Questions** - Product info, pricing, availability
2. **Check Inventory** - Real-time stock queries
3. **Process Orders** - Create and track orders
4. **Handle Payments** - Payment status and confirmation
5. **Escalate** - Hand off to human when needed

### Agent Tools

- `search_products_by_name` - Find products
- `get_product_details` - Product specifications
- `check_stock_by_product_id` - Inventory levels
- `create_order` - Place new order
- `get_payment_status` - Check payment state

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check import errors
cd backend
source .venv/bin/activate
python -c "from runner import runner_hook; print('OK')"
```

### Agent not replying
- Check `backend/runner.py` - ensure agent is enabled (not returning fallback)
- Check logs for agent execution errors
- Verify OpenAI API key is set

### Webhook not receiving messages
- Verify webhook URL in Meta dashboard
- Check verify token matches
- Use ngrok for local testing: `ngrok http 8000`
- Update webhook URL in Meta to ngrok URL

### Frontend not showing customers
- Check vendorId is set in VendorContext
- Verify backend is running and accessible
- Check browser console for API errors
- Ensure vendor exists in `backend/db/vendors.json`

## 📝 Next Steps

### For Production

1. **Database** - Switch from JSON files to PostgreSQL/MongoDB
2. **Authentication** - Add vendor login system
3. **WebSockets** - Real-time message updates without refresh
4. **Media Support** - Handle images, documents, audio
5. **Analytics** - Track conversations, response times, sales
6. **Multi-Agent** - Route to specialized agents by topic
7. **Human Handoff** - Escalation to live support

### For Testing

1. Run test script: `python test_webhook_flow.py`
2. Send real WhatsApp message to business number
3. Check dashboard updates immediately
4. Verify agent replies make sense
5. Test different conversation flows

## 🎉 Success Criteria

When everything works:

✅ Customer messages your WhatsApp Business number  
✅ Webhook receives message instantly  
✅ Customer appears in `/dashboard/sales/my-users`  
✅ Agent replies automatically within seconds  
✅ Both messages show in `/dashboard/sales/history`  
✅ Conversation continues naturally with agent  
✅ All history persists in database  

You now have a fully automated WhatsApp sales agent! 🚀
