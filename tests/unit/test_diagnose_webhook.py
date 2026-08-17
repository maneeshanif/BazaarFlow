#!/usr/bin/env python3
"""
Complete webhook diagnostics tool.
Tests if Meta can reach your webhook and if messages are being processed.
"""

import asyncio
import json
import sys

import httpx


async def test_complete_webhook_flow():
    """Run all webhook tests."""
    
    print("🔍 COMPLETE WEBHOOK DIAGNOSTICS")
    print("=" * 80)
    print()
    
    # Configuration
    LOCAL_URL = "http://localhost:8000"
    NGROK_URL = "https://planiform-doctrinally-lynnette.ngrok-free.dev"
    
    results = []
    
    # Test 1: Backend health
    print("1️⃣  Testing Backend Health...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{LOCAL_URL}/health")
            if response.status_code == 200:
                print("   ✅ Backend is running")
                results.append(("Backend Health", True))
            else:
                print(f"   ❌ Backend returned {response.status_code}")
                results.append(("Backend Health", False))
    except Exception as e:
        print(f"   ❌ Cannot reach backend: {e}")
        results.append(("Backend Health", False))
        return
    print()
    
    # Test 2: Webhook test endpoint
    print("2️⃣  Testing Webhook Test Endpoint...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{LOCAL_URL}/webhook/test")
            if response.status_code == 200:
                print("   ✅ Webhook endpoint is accessible")
                results.append(("Webhook Accessible", True))
            else:
                print(f"   ❌ Webhook returned {response.status_code}")
                results.append(("Webhook Accessible", False))
    except Exception as e:
        print(f"   ❌ Webhook not accessible: {e}")
        results.append(("Webhook Accessible", False))
    print()
    
    # Test 3: Webhook verification (GET)
    print("3️⃣  Testing Webhook Verification (Meta Challenge)...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{LOCAL_URL}/webhook",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": "test123",
                    "hub.challenge": "CHALLENGE_12345"
                }
            )
            if response.status_code == 200 and response.text == "CHALLENGE_12345":
                print("   ✅ Webhook verification working")
                print("   📝 Meta can verify your webhook URL")
                results.append(("Webhook Verification", True))
            else:
                print(f"   ❌ Verification failed: {response.status_code}")
                results.append(("Webhook Verification", False))
    except Exception as e:
        print(f"   ❌ Verification error: {e}")
        results.append(("Webhook Verification", False))
    print()
    
    # Test 4: ngrok tunnel
    print("4️⃣  Testing ngrok Tunnel...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:4040/api/tunnels")
            tunnels = response.json().get("tunnels", [])
            
            if tunnels:
                for tunnel in tunnels:
                    public_url = tunnel.get("public_url", "")
                    if public_url.startswith("https"):
                        print(f"   ✅ ngrok tunnel active")
                        print(f"   🌐 Public URL: {public_url}")
                        print()
                        print(f"   📋 Use this in Meta webhook:")
                        print(f"      {public_url}/webhook")
                        results.append(("ngrok Active", True))
                        break
            else:
                print("   ❌ No ngrok tunnels found")
                print("   👉 Start ngrok: ngrok http 8000")
                results.append(("ngrok Active", False))
    except Exception:
        print("   ⚠️  Cannot check ngrok (may not be running)")
        print("   👉 Start ngrok: ngrok http 8000")
        results.append(("ngrok Active", False))
    print()
    
    # Test 5: Test message via ngrok
    print("5️⃣  Testing Message Processing via ngrok...")
    test_webhook_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "1490360058646099",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "15550123456",
                        "phone_number_id": "710222118850893",
                        "wa_id": "1490360058646099"
                    },
                    "contacts": [{
                        "profile": {"name": "Diagnostic Test"},
                        "wa_id": "923999999999"
                    }],
                    "messages": [{
                        "from": "923999999999",
                        "id": "wamid.diagnostic123",
                        "timestamp": "1731524400",
                        "text": {"body": "Diagnostic test message"},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{NGROK_URL}/webhook",
                json=test_webhook_payload
            )
            if response.status_code == 200:
                print("   ✅ Webhook accepted test message")
                print("   🔄 Message processing successful")
                results.append(("Message Processing", True))
                
                # Check if customer was saved
                await asyncio.sleep(1)
                
                # Get vendor ID from database
                vendors_response = await client.get(f"{LOCAL_URL}/api/vendors")
                vendors = vendors_response.json()
                
                if vendors:
                    vendor_id = vendors[0]["vendor_id"]
                    customers_response = await client.get(
                        f"{LOCAL_URL}/api/vendors/{vendor_id}/customers"
                    )
                    customers = customers_response.json().get("customers", [])
                    
                    diagnostic_customer = next(
                        (c for c in customers if c["phone"] == "923999999999"),
                        None
                    )
                    
                    if diagnostic_customer:
                        print("   ✅ Customer saved to database")
                        print(f"   📱 Customer: {diagnostic_customer['phone']}")
                    else:
                        print("   ⚠️  Customer not found in database")
            else:
                print(f"   ❌ Webhook returned {response.status_code}")
                results.append(("Message Processing", False))
    except Exception as e:
        print(f"   ❌ Test message failed: {e}")
        results.append(("Message Processing", False))
    print()
    
    # Summary
    print("=" * 80)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 80)
    print()
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}  {test_name}")
    print()
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print()
        print("Your webhook is fully configured and working.")
        print("Meta should be able to send messages to your backend.")
        print()
        print("If real messages still don't work:")
        print("1. Verify Meta webhook URL matches your ngrok URL")
        print("2. Check 'messages' field is subscribed in Meta")
        print("3. Send test message from WhatsApp to your business number")
        print("4. Watch backend terminal for webhook logs")
    else:
        print("⚠️  SOME TESTS FAILED")
        print()
        print("Fix the failed tests above, then:")
        print("1. Make sure backend is running: fastapi dev app.py")
        print("2. Make sure ngrok is running: ngrok http 8000")
        print("3. Update Meta webhook with ngrok URL")
        print("4. Run this diagnostic again")
    
    print()
    print("=" * 80)
    print()
    print("💡 TIP: Watch backend terminal for detailed webhook logs")
    print("   Look for lines starting with 🔍 📨 ✅ ❌")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(test_complete_webhook_flow())
    except KeyboardInterrupt:
        print("\n\n⏸️  Diagnostic interrupted by user")
        sys.exit(0)
