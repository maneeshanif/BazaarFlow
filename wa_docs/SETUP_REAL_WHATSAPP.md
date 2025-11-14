# 🚀 Set Up Real WhatsApp Messages - Step by Step

## Current Situation:
- ✅ Backend running on `localhost:8000`
- ✅ Test script works (test_webhook_flow.py)
- ❌ Real WhatsApp messages NOT reaching your backend
- ❌ Your friend's messages are lost

## Why Real Messages Don't Work:

```
Meta WhatsApp API → Needs PUBLIC URL → But you have localhost:8000 ❌
```

Meta can't reach `localhost:8000` from the internet!

---

## 🎯 Step-by-Step Fix

### Step 1: Install ngrok (If not installed)

```bash
# Download ngrok
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | \
  sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && \
  echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | \
  sudo tee /etc/apt/sources.list.d/ngrok.list && \
  sudo apt update && sudo apt install ngrok
```

Or download from: https://ngrok.com/download

### Step 2: Start ngrok (New Terminal 4)

```bash
ngrok http 8000
```

**You'll see output like:**
```
Session Status    online
Account           your@email.com
Version           3.x.x
Region            United States (us)
Forwarding        https://a1b2c3d4.ngrok.io -> http://localhost:8000

Connections       ttl     opn     rt1     rt5     p50     p90
                  0       0       0.00    0.00    0.00    0.00
```

**Copy the HTTPS URL**: `https://a1b2c3d4.ngrok.io`

### Step 3: Configure Meta Webhook

1. Go to: https://developers.facebook.com/apps
2. Select your app
3. Left sidebar: **WhatsApp** → **Configuration**

4. **In Webhook section:**
   - Click **Edit** or **Configure Webhook**
   - **Callback URL**: `https://a1b2c3d4.ngrok.io/webhook` (use YOUR ngrok URL)
   - **Verify Token**: `test123`
   - Click **Verify and Save**

5. **Subscribe to webhooks:**
   - Find **Webhook fields** section
   - Toggle ON: **messages**
   - Click **Subscribe**

### Step 4: Test with Real WhatsApp

1. **Your friend sends message** to your WhatsApp Business number
2. **Watch ngrok terminal** - you'll see:
   ```
   POST /webhook  200 OK
   ```

3. **Check backend terminal** - you'll see:
   ```
   INFO: Webhook POST received
   DEBUG: Runner hook invoking agent
   ```

4. **Check database files:**
   ```bash
   cat backend/db/customers.json
   # Should show your friend's phone number
   
   cat backend/db/messages.json
   # Should show 2 messages (friend + agent reply)
   ```

5. **Your friend receives agent reply** on WhatsApp instantly! 🎉

---

## 🔍 Troubleshooting

### Issue: "Webhook verification failed"

**Solution:** Make sure:
- ngrok is running: `ngrok http 8000`
- Backend is running: `fastapi dev app.py`
- Verify token is exactly: `test123`
- URL format: `https://xxxxx.ngrok.io/webhook` (don't forget `/webhook`)

### Issue: "Messages not appearing in database"

**Check backend logs:**
```bash
# In backend terminal, you should see:
INFO: Webhook POST received: keys=['object', 'entry']
DEBUG: Runner hook invoking agent for vendor d2f0e426-b0ee-4590-88d0-663133267a98
```

If you don't see these logs, Meta webhook is not configured correctly.

### Issue: "Agent not replying"

**Check:**
1. Backend logs for errors
2. Access token is valid in `backend/db/vendors.json`
3. Phone number ID matches your WhatsApp Business number

---

## ✅ Success Checklist

After setup, test:

- [ ] ngrok running and showing HTTPS URL
- [ ] Meta webhook configured with ngrok URL
- [ ] Friend sends "Hello" to your WhatsApp Business number
- [ ] Backend logs show webhook received
- [ ] `customers.json` has friend's phone number
- [ ] `messages.json` has 2 messages (inbound + outbound)
- [ ] Friend receives agent reply on WhatsApp
- [ ] Dashboard shows friend in `/my-users`
- [ ] Dashboard shows conversation in `/history`

---

## 🎯 Quick Commands Summary

### Terminal 1: Backend
```bash
cd backend
source .venv/bin/activate
fastapi dev app.py
```

### Terminal 2: Frontend
```bash
cd frontend
npm run dev
```

### Terminal 3: ngrok (NEW!)
```bash
ngrok http 8000
# Copy the HTTPS URL and use it in Meta webhook
```

### Terminal 4: Monitor
```bash
# Watch database updates in real-time
watch -n 1 'cat backend/db/customers.json | jq'
```

---

## 🎉 What Happens After Setup

1. **Any customer** messages your WhatsApp number
2. **Meta sends webhook** to your ngrok URL
3. **Your backend** receives it and processes
4. **Customer saved** to database automatically
5. **AI Agent** generates smart reply
6. **Reply sent** via WhatsApp API
7. **Message history** saved for dashboard
8. **Customer sees reply** on WhatsApp instantly
9. **You see everything** in dashboard

---

## 📱 Example Flow

```
Friend: "Hi, do you have laptops?"
  ↓
Meta WhatsApp → https://your.ngrok.io/webhook
  ↓
Your Backend receives webhook
  ↓
Saves customer: Friend's phone number
  ↓
Saves message: "Hi, do you have laptops?"
  ↓
AI Agent processes request
  ↓
Agent: "👋 Yes! We have Dell XPS, MacBook Air, and Lenovo ThinkPad. 
       What's your budget?"
  ↓
Saves agent reply to database
  ↓
Sends reply via WhatsApp API
  ↓
Friend receives reply on WhatsApp ✅
  ↓
Dashboard shows customer + conversation ✅
```

---

## 🔒 Security Note

ngrok free tier gives you a random URL that changes each restart. For production:
- Use ngrok paid plan for static URL
- Or deploy backend to cloud (Railway, Render, DigitalOcean)
- Update Meta webhook URL whenever ngrok restarts

---

## 🆘 Need Help?

If webhook still not working:

1. Check ngrok terminal for incoming requests
2. Check backend terminal for processing logs
3. Verify Meta webhook configuration matches ngrok URL exactly
4. Test webhook using Meta's "Test" button in webhook configuration
5. Check `backend/db/vendors.json` has correct access_token

Your setup is ready - just need to connect Meta to your backend! 🚀
