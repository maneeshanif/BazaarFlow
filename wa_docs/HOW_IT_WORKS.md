# 🎯 How BazaarFlow Works - Complete Flow Explained

## 📱 The Complete Customer → Agent Flow

### Your Setup (One Time Only)

```
1. You create vendor account in dashboard
2. You save WhatsApp credentials (Phone Number ID, WABA ID, Token)
3. Done! ✅ Your business is ready to receive messages
```

**Your Vendor Info:**
- Vendor ID: `d2f0e426-b0ee-4590-88d0-663133267a98`
- Phone Number ID: `710222118850893` (Your WhatsApp Business Number)
- WABA ID: `1490360058646099`

---

## 🔄 What Happens When Customer Messages You

### Step 1: Customer Sends Message
```
Customer (e.g., +92 300 1234567) 
    ↓
Sends WhatsApp message
    ↓
To YOUR business number (710222118850893)
```

### Step 2: Meta Sends Webhook to Your Backend
```json
{
  "entry": [{
    "changes": [{
      "value": {
        "metadata": {
          "phone_number_id": "710222118850893"  ← YOUR NUMBER
        },
        "contacts": [{
          "wa_id": "923001234567",  ← CUSTOMER'S NUMBER
          "profile": { "name": "Ahmad" }
        }],
        "messages": [{
          "from": "923001234567",
          "text": { "body": "Hello, I want to buy products" }
        }]
      }
    }]
  }]
}
```

### Step 3: Backend Processes (webhook.py)

```python
# Line 80-84: Find or create vendor by phone_number_id
vendor = repository.upsert_vendor(
    phone_number_id="710222118850893",  # YOUR business number
    name=vendor_name,
    waba_id="1490360058646099"
)
# Result: vendor_id = "d2f0e426-b0ee-4590-88d0-663133267a98"

# Line 91-94: Create customer record
customer = repository.upsert_customer(
    vendor["vendor_id"],  # Links to YOUR vendor
    phone="923001234567",  # Customer's phone
    name="Ahmad"
)
# Result: New customer linked to YOUR vendor

# Line 101-108: Save incoming message
repository.record_message(
    vendor_id="d2f0e426-b0ee-4590-88d0-663133267a98",  # YOUR vendor
    customer_phone="923001234567",  # CUSTOMER
    direction="inbound",
    text="Hello, I want to buy products",
    timestamp="2025-11-12T15:30:00Z"
)
```

### Step 4: AI Agent Processes Message

```python
# Line 110-115: Call AI agent
action = await runner_hook(
    vendor=vendor,  # YOUR business info
    customer=customer,  # Customer who messaged
    incoming_message={"text": "Hello, I want to buy products"},
    metadata=metadata
)

# Agent thinks:
# "Customer wants to buy products"
# "Let me check inventory..."
# "Generate helpful response..."

# Returns:
# {
#   "reply_text": "Hi Ahmad! 👋 I'd be happy to help you find products. 
#                  What are you looking for today?",
#   "action": "reply"
# }
```

### Step 5: Send Reply to Customer

```python
# Line 124-134: Send WhatsApp message
response = await send_text_message(
    phone_number_id="710222118850893",  # YOUR number
    access_token="EAAG...",  # YOUR token
    to="923001234567",  # CUSTOMER
    body="Hi Ahmad! 👋 I'd be happy to help..."
)

# Customer receives message on WhatsApp instantly!
```

### Step 6: Save Agent's Reply

```python
# Line 136-144: Record outbound message
repository.record_message(
    vendor_id="d2f0e426-b0ee-4590-88d0-663133267a98",  # YOUR vendor
    customer_phone="923001234567",  # CUSTOMER
    direction="outbound",
    text="Hi Ahmad! 👋 I'd be happy to help...",
    timestamp="2025-11-12T15:30:02Z"
)
```

---

## 📊 Database After Customer Messages

### vendors.json (Stays the same - YOUR business)
```json
[{
  "vendor_id": "d2f0e426-b0ee-4590-88d0-663133267a98",
  "phone_number_id": "710222118850893",
  "name": "Your Business",
  "access_token": "EAAG..."
}]
```

### customers.json (NEW customer appears)
```json
[{
  "id": "abc-123-def",
  "vendor_id": "d2f0e426-b0ee-4590-88d0-663133267a98",  ← Links to YOU
  "phone": "923001234567",  ← Customer's number
  "name": "Ahmad",
  "first_seen": "2025-11-12T15:30:00Z",
  "last_seen": "2025-11-12T15:30:00Z"
}]
```

### messages.json (2 messages - IN and OUT)
```json
[
  {
    "id": "msg-1",
    "vendor_id": "d2f0e426-b0ee-4590-88d0-663133267a98",  ← YOUR vendor
    "customer_phone": "923001234567",  ← CUSTOMER
    "direction": "inbound",
    "text": "Hello, I want to buy products",
    "timestamp": "2025-11-12T15:30:00Z"
  },
  {
    "id": "msg-2",
    "vendor_id": "d2f0e426-b0ee-4590-88d0-663133267a98",  ← YOUR vendor
    "customer_phone": "923001234567",  ← CUSTOMER
    "direction": "outbound",
    "text": "Hi Ahmad! 👋 I'd be happy to help you find products...",
    "timestamp": "2025-11-12T15:30:02Z"
  }
]
```

---

## 👥 Multiple Customers? No Problem!

### Scenario: 3 Different Customers Message You

**Customer 1:** +92 300 1234567 (Ahmad)
**Customer 2:** +92 301 9876543 (Sara)  
**Customer 3:** +92 302 5555555 (Hassan)

### Database Structure:

```
vendors.json:
└── YOUR VENDOR (d2f0e426-b0ee-4590-88d0-663133267a98)

customers.json:
├── Ahmad (923001234567) → vendor_id: d2f0e426...
├── Sara (923019876543) → vendor_id: d2f0e426...
└── Hassan (923025555555) → vendor_id: d2f0e426...

messages.json:
├── Ahmad's conversation:
│   ├── [inbound] Ahmad: "Hi"
│   ├── [outbound] Agent: "Hello Ahmad!"
│   ├── [inbound] Ahmad: "Show products"
│   └── [outbound] Agent: "Here are our products..."
│
├── Sara's conversation:
│   ├── [inbound] Sara: "Price check"
│   └── [outbound] Agent: "Sure! What product?"
│
└── Hassan's conversation:
    ├── [inbound] Hassan: "Order status?"
    └── [outbound] Agent: "Let me check..."
```

**Key Point:** Every message has:
- `vendor_id` → YOUR business
- `customer_phone` → Specific customer
- This combination keeps conversations separate!

---

## 🖥️ Dashboard View

### `/dashboard/sales/my-users` Shows:

```
┌─────────────────────────────────────────┐
│ Customer Directory                       │
├─────────────────────────────────────────┤
│                                          │
│  📱 Ahmad                    [Active]    │
│     +92 300 1234567                      │
│     Last seen: 2 mins ago                │
│     [View conversation →]                │
│                                          │
│  📱 Sara                     [Recent]    │
│     +92 301 9876543                      │
│     Last seen: 30 mins ago               │
│     [View conversation →]                │
│                                          │
│  📱 Hassan                   [Active]    │
│     +92 302 5555555                      │
│     Last seen: just now                  │
│     [View conversation →]                │
│                                          │
└─────────────────────────────────────────┘
```

### `/dashboard/sales/history?customer=923001234567` Shows:

```
┌─────────────────────────────────────────────────┐
│ Conversation with Ahmad (+92 300 1234567)       │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────────────────────────┐           │
│  │ Hello, I want to buy products    │ ← Customer│
│  └──────────────────────────────────┘           │
│  🕐 2:30 PM                                      │
│                                                  │
│         ┌────────────────────────────────────┐  │
│  Agent →│ Hi Ahmad! 👋 I'd be happy to help  │  │
│         │ you find products. What are you    │  │
│         │ looking for today?                 │  │
│         └────────────────────────────────────┘  │
│         🕐 2:30 PM                               │
│                                                  │
│  ┌──────────────────────────────────┐           │
│  │ Show me laptops                  │ ← Customer│
│  └──────────────────────────────────┘           │
│  🕐 2:31 PM                                      │
│                                                  │
│         ┌────────────────────────────────────┐  │
│  Agent →│ Great choice! We have Dell XPS 13, │  │
│         │ MacBook Air, and Lenovo ThinkPad.  │  │
│         │ Which one interests you?           │  │
│         └────────────────────────────────────┘  │
│         🕐 2:31 PM                               │
│                                                  │
└─────────────────────────────────────────────────┘
```

---

## 🎯 Key Points - How Vendor/Customer Distinction Works

### 1. Vendor Identification
```python
# Webhook identifies YOUR vendor by phone_number_id
phone_number_id = metadata.get("phone_number_id")  # "710222118850893"
vendor = repository.upsert_vendor(phone_number_id=phone_number_id)
# Returns: YOUR vendor record
```

### 2. Customer Identification
```python
# Webhook identifies customer by their phone number
customer_phone = message.get("from")  # "923001234567"
customer = repository.upsert_customer(
    vendor["vendor_id"],  # Links to YOUR vendor
    phone=customer_phone
)
# Creates/updates customer under YOUR vendor
```

### 3. Message Storage
```python
# Every message links vendor + customer
repository.record_message(
    vendor_id="d2f0e426-b0ee-4590-88d0-663133267a98",  # YOU
    customer_phone="923001234567",  # THEM
    direction="inbound" or "outbound",
    text="message content"
)
```

### 4. Conversation Retrieval
```python
# Frontend fetches messages for specific vendor + customer pair
messages = repository.list_messages(
    vendor_id="d2f0e426-b0ee-4590-88d0-663133267a98",  # YOUR vendor
    customer_phone="923001234567"  # Specific customer
)
# Returns only messages between YOU and THIS customer
```

---

## ✅ Summary - What You Asked For

| Requirement | Status | How It Works |
|------------|--------|--------------|
| Vendor created once | ✅ Done | You saved credentials in settings |
| Customer messages saved | ✅ Auto | Webhook creates customer on first message |
| Messages linked to vendor | ✅ Yes | Every message has `vendor_id` field |
| Messages linked to customer | ✅ Yes | Every message has `customer_phone` field |
| Agent auto-replies | ✅ Yes | `runner_hook` processes and sends reply |
| History saved | ✅ Yes | Both inbound and outbound in `messages.json` |
| Can distinguish customers | ✅ Yes | Each customer has unique phone + linked to vendor |

---

## 🚀 Test It Now

### Start Backend:
```bash
cd backend
source .venv/bin/activate
fastapi dev app.py
```

### Run Test Script:
```bash
python test_webhook_flow.py
```

### Check Dashboard:
```
http://localhost:3000/dashboard/sales/my-users
```

You'll see:
1. ✅ Test customer appears
2. ✅ Linked to your vendor
3. ✅ Conversation history shows both messages
4. ✅ Agent replied automatically

**It's already working exactly as you requested!** 🎉
