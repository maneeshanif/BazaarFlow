# 🚀 Quick Start - Test Your WhatsApp Agent NOW

## ✅ Prerequisites Check

Your system is ready with:
- ✅ Vendor created and credentials saved
- ✅ Backend agent enabled and ready
- ✅ Frontend dashboard built and working
- ✅ All import issues fixed
- ✅ Database files initialized

## 🎬 Start in 3 Steps

### 1️⃣ Start Backend (Terminal 1)

```bash
cd /home/maneeshanif/Desktop/code\ /python-prjs/hackthon_final/BazaarFlow/backend
source .venv/bin/activate
fastapi dev app.py
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Starting BazaarFlow FastAPI app
```

### 2️⃣ Start Frontend (Terminal 2)

```bash
cd /home/maneeshanif/Desktop/code\ /python-prjs/hackthon_final/BazaarFlow/frontend
npm run dev
```

**Expected output:**
```
  ▲ Next.js 15.x
  - Local:        http://localhost:3000
```

### 3️⃣ Test Webhook (Terminal 3)

```bash
cd /home/maneeshanif/Desktop/code\ /python-prjs/hackthon_final/BazaarFlow/backend
source .venv/bin/activate
python test_webhook_flow.py
```

## 📱 View Results in Dashboard

1. Open browser: `http://localhost:3000/dashboard/sales/my-users`
2. You should see **Test Customer (923001234567)**
3. Click **"View conversation"**
4. See the message exchange:
   - 📨 **Customer**: "Hi, I want to check product availability"
   - 🤖 **Agent**: [Intelligent reply from your sales agent]

## 🎯 What Happens When You Run test_webhook_flow.py

```
1. 📤 Sends fake WhatsApp message to webhook
2. 🔄 Webhook processes message
3. 👤 Creates customer: 923001234567 (Test Customer)
4. 💾 Stores inbound message
5. 🤖 AI Agent processes request
6. 💬 Agent generates reply
7. 💾 Stores outbound message
8. 📊 Shows results in terminal
```

## 🔍 Verification Checklist

After running test script, verify:

- [ ] Terminal shows: ✅ Response status: 200
- [ ] Terminal shows: 👥 Customers: [{"id": "...", "phone": "923001234567"}]
- [ ] Terminal shows: 📨 Messages count: 2 (one inbound, one outbound)
- [ ] Dashboard `/my-users` shows the test customer
- [ ] Dashboard `/history` shows conversation
- [ ] Backend logs show: "Runner hook invoking agent"

## 🐛 If Something Goes Wrong

### Backend Error: Import Issues
```bash
# Re-check imports
cd backend
python -c "from runner import runner_hook; print('✅ Runner OK')"
python -c "from .my_agents.sales_agent import sales_agent; print('✅ Agent OK')"
```

### Frontend Error: Can't Connect
- Check backend is running on port 8000
- Check CORS is enabled in backend
- Open `http://localhost:8000/health` (should return `{"status": "ok"}`)

### No Agent Reply
- Check `runner.py` line 38 - should NOT return fallback immediately
- Check OpenAI API key in backend/.env
- Look for errors in backend terminal logs

## 🎉 Success Looks Like This

### Terminal Output:
```
🧪 Testing WhatsApp Webhook Flow

📤 Sending test webhook to backend...
✅ Response status: 200
📥 Response body: {'status': 'ok'}

📋 Checking if customer was registered...
👥 Customers: {'customers': [{'id': '...', 'phone': '923001234567', 'name': 'Test Customer'}]}

💬 Checking conversation history...
📨 Messages count: 2
  inbound: Hi, I want to check product availability
  outbound: [Agent's intelligent reply]
```

### Dashboard View:
![Dashboard showing customer and messages]

## 🚀 Next: Test with Real WhatsApp

### Option 1: Use ngrok (Easiest for Testing)

```bash
# Terminal 4
ngrok http 8000
```

Copy the ngrok URL (e.g., `https://abc123.ngrok.io`)

### Option 2: Deploy to Server

Deploy backend to cloud server with public IP

### Configure Meta Webhook

1. Go to: https://developers.facebook.com/apps
2. Select your app
3. WhatsApp → Configuration
4. Webhook:
   - Callback URL: `https://your-ngrok-url.ngrok.io/webhook`
   - Verify Token: `test123`
   - Subscribe to: `messages`

### Send Real Message

1. Use WhatsApp on your phone
2. Message your business number: `+1 555 012 3456`
3. Type: "Hello, what products do you have?"
4. Watch agent reply instantly! 🎉
5. Check dashboard - conversation appears in real-time

## 📊 Monitor Everything

### Backend Logs
Watch terminal 1 for:
- `Webhook POST received`
- `Runner hook invoking agent`
- Message send confirmations

### Database Files
```bash
# Watch real-time updates
watch -n 1 'cat backend/db/customers.json | jq'
watch -n 1 'cat backend/db/messages.json | jq'
```

### Frontend Console
Open browser DevTools → Console to see:
- API calls
- Data fetching
- State updates

## 🎯 You're Ready!

Everything is set up correctly. Just:
1. Start backend
2. Start frontend  
3. Run test script
4. See it work!

For production use, configure ngrok and Meta webhook.

Happy testing! 🚀✨
