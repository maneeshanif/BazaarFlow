# 🔗 Webhook Setup Guide - Connect WhatsApp to Your Backend

## ⚠️ Current Issue

When customers message your WhatsApp Business number, **Meta doesn't know where to send the webhook event**. That's why:

- ❌ Customer details not saved in `customers.json`
- ❌ Messages not appearing in dashboard
- ❌ Agent not replying back

## ✅ Solution: Configure Meta Webhook

You have 2 options:

---

## 🚀 Option 1: Quick Test with ngrok (Recommended for Testing)

### Step 1: Install ngrok

```bash
# Download from https://ngrok.com/download
# Or using snap
sudo snap install ngrok
```

### Step 2: Start ngrok Tunnel

```bash
# In a new terminal
ngrok http 8000
```

You'll see output like:
```
ngrok

Session Status                online
Account                       Your Name (Plan: Free)
Version                       3.x.x
Region                        United States (us)
Latency                       45ms
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123xyz.ngrok-free.app -> http://localhost:8000

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

**Copy the HTTPS URL**: `https://abc123xyz.ngrok-free.app`

### Step 3: Configure Meta Webhook

1. Go to: https://developers.facebook.com/apps
2. Select your WhatsApp app
3. Click **WhatsApp** → **Configuration**
4. Under **Webhook**, click **Edit**
5. Enter:
   - **Callback URL**: `https://abc123xyz.ngrok-free.app/webhook`
   - **Verify Token**: `test123`
6. Click **Verify and Save**

### Step 4: Subscribe to Messages

1. In Webhook Fields, click **Manage**
2. Check ✅ **messages**
3. Click **Subscribe**

### Step 5: Test It!

1. Send a WhatsApp message from your phone to your business number
2. Watch backend terminal - you should see logs
3. Check ngrok dashboard: `http://localhost:4040`
4. Check `backend/db/customers.json` - customer should appear
5. Check dashboard: `http://localhost:3000/dashboard/sales/my-users`

---

## 🌐 Option 2: Deploy to Production Server

### Requirements:
- VPS/Cloud server with public IP
- Domain name (optional but recommended)
- SSL certificate (required for Meta webhook)

### Quick Deploy with Railway/Render/Fly.io:

1. **Deploy Backend**:
   ```bash
   # Push to GitHub
   git add .
   git commit -m "Ready for deployment"
   git push origin feature/wiring-up-all-agents
   
   # Deploy on Railway/Render
   # Set PORT environment variable to 8000
   ```

2. **Get Public URL**: e.g., `https://yourapp.railway.app`

3. **Configure Meta Webhook**:
   - Callback URL: `https://yourapp.railway.app/webhook`
   - Verify Token: `test123`

---

## 🧪 Option 3: Test Locally Without Real WhatsApp

While setting up ngrok, you can test the complete flow locally:

### Run Test Script

```bash
cd backend
source .venv/bin/activate
python test_webhook_flow.py
```

This simulates a real WhatsApp message and:
- ✅ Creates customer in `customers.json`
- ✅ Saves messages in `messages.json`
- ✅ Agent processes and replies
- ✅ Shows in dashboard

### Expected Output:

```
🧪 Testing WhatsApp Webhook Flow

Make sure backend is running on http://localhost:8000

📤 Sending test webhook to backend...
✅ Response status: 200
📥 Response body: {'status': 'ok'}

📋 Checking if customer was registered...
👥 Customers: {'customers': [{'id': '...', 'phone': '923001234567', 'name': 'Test Customer', ...}]}

💬 Checking conversation history...
📨 Messages count: 2
  inbound: Hi, I want to check product availability
  outbound: Thanks for reaching out! A sales specialist will follow up shortly.
```

### View in Dashboard:

1. Open: `http://localhost:3000/dashboard/sales/my-users`
2. See test customer: `923001234567`
3. Click "View conversation"
4. See full message history

---

## 🔍 Troubleshooting

### Issue: Webhook verification failed

**Error**: "The URL couldn't be validated. Callback verification failed with the following errors..."

**Solution**:
1. Make sure backend is running
2. Check ngrok is forwarding to port 8000
3. Verify token matches `META_VERIFY_TOKEN` in backend (default: `test123`)
4. Check ngrok URL is HTTPS (not HTTP)

### Issue: Messages not appearing in dashboard

**Check**:
```bash
# 1. Is webhook receiving requests?
# Check ngrok dashboard: http://localhost:4040

# 2. Are customers being created?
cat backend/db/customers.json

# 3. Are messages being saved?
cat backend/db/messages.json

# 4. Check backend logs
# Look in terminal where fastapi dev is running
```

### Issue: Agent not replying

**Check**:
```bash
# 1. Is OPENAI_API_KEY set?
grep OPENAI_API_KEY backend/.env

# 2. Check runner.py is not returning fallback immediately
# Line 38 should NOT be: return {"reply_text": _FALLBACK_REPLY, "action": "reply"}

# 3. Check backend logs for errors
# Look for "Runner hook invoking agent"
```

### Issue: ngrok session expired

Free ngrok URLs expire when you close the tunnel. When you restart ngrok, you get a NEW URL.

**Solution**:
1. Get new ngrok URL
2. Update Meta webhook with new URL
3. Or upgrade to ngrok paid plan for persistent URLs

---

## 📝 Environment Variables

### backend/.env

```bash
# Meta WhatsApp
META_VERIFY_TOKEN=test123

# OpenAI (for agent)
OPENAI_API_KEY=sk-proj-...your-key-here...

# Frontend URL (for CORS)
FRONTEND_ORIGIN=http://localhost:3000

# Optional: Production mode
# PRODUCTION=true
```

---

## ✅ Verification Checklist

Before testing with real WhatsApp:

- [ ] Backend running on port 8000
- [ ] Health endpoint works: `curl http://localhost:8000/health`
- [ ] ngrok tunnel active (or production URL ready)
- [ ] Meta webhook configured with correct URL
- [ ] Verify token matches in Meta and backend
- [ ] Subscribed to "messages" events in Meta
- [ ] OPENAI_API_KEY set in backend/.env
- [ ] Frontend running on port 3000

---

## 🎯 Quick Start (Full Flow)

### Terminal 1: Backend
```bash
cd backend
source .venv/bin/activate
fastapi dev app.py
```

### Terminal 2: ngrok
```bash
ngrok http 8000
# Copy the HTTPS URL
```

### Terminal 3: Frontend
```bash
cd frontend
npm run dev
```

### Browser 1: Configure Meta
1. Open: https://developers.facebook.com/apps
2. Update webhook URL with ngrok HTTPS URL
3. Verify and subscribe to messages

### Browser 2: Dashboard
1. Open: http://localhost:3000/dashboard/sales/my-users
2. Keep this tab open

### Phone: Send Test Message
1. Open WhatsApp
2. Message your business number
3. Watch dashboard refresh - customer appears!
4. See agent reply in WhatsApp

---

## 🎉 Success Looks Like

### Backend Terminal:
```
INFO:     Webhook POST received: keys=['object', 'entry']
DEBUG:    Runner hook invoking agent for vendor d2f0e426-b0ee-4590-88d0-663133267a98
INFO:     Outbound message sent to customer
```

### ngrok Dashboard (http://localhost:4040):
```
POST /webhook          200 OK      1.2s
```

### customers.json:
```json
[{
  "id": "...",
  "vendor_id": "d2f0e426-b0ee-4590-88d0-663133267a98",
  "phone": "923001234567",
  "name": "Ahmad Khan",
  "first_seen": "2025-11-12T14:52:00Z",
  "last_seen": "2025-11-12T14:52:00Z"
}]
```

### messages.json:
```json
[
  {
    "id": "...",
    "vendor_id": "d2f0e426-b0ee-4590-88d0-663133267a98",
    "customer_phone": "923001234567",
    "direction": "inbound",
    "text": "Hello, can I order something?",
    "timestamp": "2025-11-12T14:52:00Z"
  },
  {
    "id": "...",
    "vendor_id": "d2f0e426-b0ee-4590-88d0-663133267a98",
    "customer_phone": "923001234567",
    "direction": "outbound",
    "text": "Hi! I'd be happy to help you place an order...",
    "timestamp": "2025-11-12T14:52:02Z"
  }
]
```

### Dashboard:
Customer appears with conversation history! 🎉

---

## 🔗 Useful Links

- ngrok Download: https://ngrok.com/download
- Meta App Dashboard: https://developers.facebook.com/apps
- Meta Webhook Docs: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks
- ngrok Dashboard: http://localhost:4040 (when running)

---

## 💡 Pro Tips

1. **Keep ngrok running** - If you close it, URL changes and webhook breaks
2. **Use ngrok web dashboard** - Monitor all webhook requests at http://localhost:4040
3. **Check backend logs** - Most issues show up in terminal output
4. **Test with test_webhook_flow.py first** - Verify everything works before configuring real webhook
5. **Use production deployment** - For permanent solution without ngrok

---

## ❓ Common Questions

**Q: Why isn't Meta sending webhooks to localhost?**  
A: Meta servers can't access localhost. You need ngrok or public URL.

**Q: Do I need to reconfigure webhook every time?**  
A: Only if ngrok URL changes (free tier) or you restart with new tunnel.

**Q: Can I test without ngrok?**  
A: Yes! Use `test_webhook_flow.py` to simulate webhooks locally.

**Q: How do I know webhook is working?**  
A: Check ngrok dashboard (http://localhost:4040) and backend logs.

**Q: Why does agent not reply?**  
A: Check OPENAI_API_KEY is set and runner.py is calling the agent (not returning fallback).

---

**You're almost there! Just configure the webhook with ngrok and everything will work! 🚀**
