#!/usr/bin/env python3
"""Diagnostic tool to check if your webhook setup is working."""

import asyncio
import json
import os
import sys

import httpx


async def check_webhook_setup():
    """Run comprehensive webhook diagnostics."""
    
    print("🔍 BazaarFlow Webhook Diagnostics")
    print("=" * 60)
    print()
    
    # 1. Check backend is running
    print("1️⃣  Checking Backend Server...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8000/health")
            if response.status_code == 200:
                print("   ✅ Backend running on localhost:8000")
            else:
                print(f"   ❌ Backend returned status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Backend NOT accessible: {e}")
        print("   👉 Start with: cd backend && fastapi dev app.py")
        return
    print()
    
    # 2. Check webhook endpoint
    print("2️⃣  Checking Webhook Endpoint...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Test GET (webhook verification)
            response = await client.get(
                "http://localhost:8000/webhook",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": "test123",
                    "hub.challenge": "test_challenge_12345"
                }
            )
            if response.status_code == 200 and response.text == "test_challenge_12345":
                print("   ✅ Webhook verification working (GET request)")
            else:
                print(f"   ⚠️  Webhook verification issue: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Webhook endpoint error: {e}")
    print()
    
    # 3. Check database files
    print("3️⃣  Checking Database Files...")
    db_path = os.path.join("backend", "db")
    
    files = {
        "vendors.json": "Vendors (your business accounts)",
        "customers.json": "Customers (people who messaged you)",
        "messages.json": "Message history"
    }
    
    for filename, description in files.items():
        filepath = os.path.join(db_path, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = json.load(f)
                count = len(data)
                print(f"   ✅ {filename}: {count} records - {description}")
        else:
            print(f"   ❌ {filename}: NOT FOUND")
    print()
    
    # 4. Check vendor credentials
    print("4️⃣  Checking Vendor Credentials...")
    try:
        with open(os.path.join(db_path, "vendors.json"), 'r') as f:
            vendors = json.load(f)
            if not vendors:
                print("   ❌ No vendors configured!")
                print("   👉 Go to dashboard/settings and save WhatsApp credentials")
            else:
                for vendor in vendors:
                    print(f"   📱 Vendor: {vendor.get('name', 'Unnamed')}")
                    print(f"      - Phone Number ID: {vendor.get('phone_number_id', 'Missing!')}")
                    print(f"      - WABA ID: {vendor.get('waba_id', 'Missing!')}")
                    has_token = bool(vendor.get('access_token'))
                    print(f"      - Access Token: {'✅ Set' if has_token else '❌ Missing'}")
    except Exception as e:
        print(f"   ❌ Error reading vendors: {e}")
    print()
    
    # 5. Check if ngrok is running
    print("5️⃣  Checking ngrok Tunnel...")
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            # ngrok provides a local API to check status
            response = await client.get("http://localhost:4040/api/tunnels")
            tunnels = response.json().get("tunnels", [])
            
            if not tunnels:
                print("   ❌ ngrok NOT running!")
                print("   👉 Start with: ngrok http 8000")
                print()
                print("   🚨 CRITICAL: Meta cannot reach localhost:8000")
                print("   You MUST use ngrok to expose your backend!")
            else:
                for tunnel in tunnels:
                    public_url = tunnel.get("public_url", "")
                    if public_url.startswith("https"):
                        print(f"   ✅ ngrok tunnel active!")
                        print(f"      Public URL: {public_url}")
                        print()
                        print("   📋 Use this URL in Meta webhook:")
                        print(f"      {public_url}/webhook")
    except Exception:
        print("   ⚠️  Cannot check ngrok (API not accessible)")
        print("   👉 If not running, start with: ngrok http 8000")
    print()
    
    # 6. Instructions
    print("6️⃣  Next Steps:")
    print()
    print("   To receive REAL WhatsApp messages:")
    print()
    print("   A. Start ngrok (if not running):")
    print("      ngrok http 8000")
    print()
    print("   B. Copy the HTTPS URL from ngrok")
    print("      Example: https://abc123.ngrok.io")
    print()
    print("   C. Configure Meta Webhook:")
    print("      1. Go to: https://developers.facebook.com/apps")
    print("      2. Select your WhatsApp app")
    print("      3. WhatsApp → Configuration → Webhook")
    print("      4. Callback URL: https://YOUR-NGROK-URL.ngrok.io/webhook")
    print("      5. Verify Token: test123")
    print("      6. Subscribe to: messages")
    print()
    print("   D. Test by sending WhatsApp message to your business number")
    print()
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(check_webhook_setup())
