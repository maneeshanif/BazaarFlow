# ✅ Webhook Setup Verification Checklist

## Your Current Configuration:
- **Vendor ID**: `f8add875-6bff-4f1a-99f5-f8e5d3ec3b67`
- **Phone Number ID**: `710222118850893`
- **WABA ID**: `1490360058646099`
- **Access Token**: ✅ Configured (permanent)
- **ngrok URL**: `https://planiform-doctrinally-lynnette.ngrok-free.dev`

---

## ✅ Checklist - Complete ALL Steps:

### 1. Meta Webhook Configuration
Go to: https://developers.facebook.com/apps

- [ ] Select your WhatsApp app
- [ ] Click **WhatsApp** → **Configuration**
- [ ] Find **Webhook** section
- [ ] Callback URL is EXACTLY:
  ```
  https://planiform-doctrinally-lynnette.ngrok-free.dev/webhook
  ```
- [ ] Verify Token is: `test123`
- [ ] Click **Verify and Save** (must show green checkmark ✓)
- [ ] **messages** webhook field is SUBSCRIBED (toggle ON)

### 2. Test Message Subscription
- [ ] In Meta, find **Webhook fields** section
- [ ] Make sure these are checked:
  - [x] **messages** ← CRITICAL!
  - [ ] messages_status (optional)
  
### 3. Phone Number Setup
- [ ] Your WhatsApp Business number is active
- [ ] Phone number is verified in Meta
- [ ] Phone number matches: `710222118850893`

### 4. Test Real Message
- [ ] Ask someone to send WhatsApp message to your business number
- [ ] Watch backend terminal for logs:
  ```
  🔔 Processing webhook message from customer
  ✅ Customer saved: 92XXXXXXXXX
  ```
- [ ] Check database:
  ```bash
  cat backend/db/customers.json  # Should show real customer
  cat backend/db/messages.json   # Should show real message
  ```

### 5. Verify ngrok is Running
- [ ] ngrok is still running in terminal
- [ ] ngrok URL hasn't changed
- [ ] If ngrok restarted, UPDATE Meta webhook with new URL!

---

## 🧪 Quick Test

Run this to simulate Meta sending a webhook:
```bash
cd backend
source .venv/bin/activate
python test_ngrok_webhook.py
```

If this works but real messages don't → Meta webhook is not configured correctly.

---

## 🐛 Troubleshooting

### Issue: Messages not appearing in database

**Check 1: Meta Webhook URL**
```bash
# In Meta, verify Callback URL is exactly:
https://planiform-doctrinally-lynnette.ngrok-free.dev/webhook
```

**Check 2: Webhook Subscriptions**
```
In Meta Dashboard:
WhatsApp → Configuration → Webhook Fields
✓ messages (must be checked!)
```

**Check 3: ngrok Status**
```bash
# Check ngrok is running:
curl http://localhost:4040/api/tunnels

# Should show: 
# "public_url": "https://planiform-doctrinally-lynnette.ngrok-free.dev"
```

**Check 4: Backend Logs**
Watch your backend terminal when someone messages you. Should see:
```
🔔 Processing webhook message from customer
✅ Vendor identified: f8add875-6bff-4f1a-99f5-f8e5d3ec3b67
✅ Customer saved: 92XXXXXXXXX (Customer Name)
💬 Message text: [actual message]
🤖 Calling AI agent to generate reply...
```

If you DON'T see these logs → Meta is not sending webhooks to your backend!

### Issue: ngrok URL changed

ngrok free tier gives random URL on each restart. If you restarted ngrok:

1. Get new URL: `curl http://localhost:4040/api/tunnels | jq '.tunnels[0].public_url'`
2. Update Meta webhook with NEW URL
3. Verify and save in Meta

---

## ✅ Success Indicators

You'll know it's working when:

1. Someone messages your WhatsApp Business number
2. Backend terminal shows processing logs (with emojis 🔔 ✅ 💬 🤖)
3. `customers.json` has their phone number
4. `messages.json` has 2 messages (their message + agent reply)
5. They receive agent's reply on WhatsApp instantly
6. Dashboard shows them in `/my-users`

---

## 📞 Your WhatsApp Business Phone Number

People must message THIS number for it to work:
- The number associated with Phone Number ID: `710222118850893`

Ask Meta support or check your Meta Business Manager to see what actual phone number this ID represents (e.g., +1 555 012 3456).

---

## 🎯 Final Check

Everything is configured correctly on your backend side (✅ verified by test).

The ONLY remaining step is ensuring Meta webhook URL is correct:

1. Go to Meta webhook settings
2. Make sure URL is: `https://planiform-doctrinally-lynnette.ngrok-free.dev/webhook`
3. Make sure `messages` is subscribed
4. Test by having someone message your business number
5. Watch your backend terminal for logs

If you see logs → Working! ✅  
If you don't see logs → Meta webhook not configured correctly ❌
