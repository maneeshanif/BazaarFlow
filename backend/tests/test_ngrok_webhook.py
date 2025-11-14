"""Send a test webhook to verify the flow is working."""

import asyncio
import httpx

# Use the actual ngrok URL
NGROK_URL = "https://planiform-doctrinally-lynnette.ngrok-free.dev"

# Test webhook payload
TEST_WEBHOOK = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "1490360058646099",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15550123456",
                            "phone_number_id": "710222118850893",
                            "wa_id": "1490360058646099"
                        },
                        "contacts": [
                            {
                                "profile": {
                                    "name": "Test Friend"
                                },
                                "wa_id": "923001234567"
                            }
                        ],
                        "messages": [
                            {
                                "from": "923001234567",
                                "id": "wamid.test456",
                                "timestamp": "1731524400",
                                "text": {
                                    "body": "Hi, can you help me?"
                                },
                                "type": "text"
                            }
                        ]
                    },
                    "field": "messages"
                }
            ]
        }
    ]
}


async def test_webhook():
    """Test webhook via ngrok URL."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print("🧪 Testing Webhook via ngrok")
            print("=" * 60)
            print()
            print(f"📡 ngrok URL: {NGROK_URL}")
            print(f"📱 Test Customer: 923001234567")
            print(f"💬 Test Message: 'i want to check product availability'")
            print()
            
            # Test via ngrok (simulates Meta webhook)
            print("📤 Sending webhook to ngrok URL...")
            response = await client.post(f"{NGROK_URL}/webhook", json=TEST_WEBHOOK)
            print(f"✅ Response: {response.status_code}")
            print(f"📥 Body: {response.json()}")
            print()
            
            # Wait a bit for processing
            await asyncio.sleep(2)
            
            # Check database via local backend
            print("📋 Checking database...")
            customers_response = await client.get(
                "http://localhost:8000/api/vendors/f8add875-6bff-4f1a-99f5-f8e5d3ec3b67/customers"
            )
            customers = customers_response.json().get("customers", [])
            print(f"👥 Customers: {len(customers)}")
            for c in customers:
                print(f"   - {c['phone']}: {c.get('name', 'No name')}")
            print()
            
            messages_response = await client.get(
                "http://localhost:8000/api/vendors/f8add875-6bff-4f1a-99f5-f8e5d3ec3b67/customers/923001234567/messages"
            )
            messages = messages_response.json().get("messages", [])
            print(f"💬 Messages: {len(messages)}")
            for msg in messages:
                direction = "📩" if msg["direction"] == "inbound" else "🤖"
                print(f"   {direction} {msg.get('text', '(no text)')[:60]}")
            print()
            
            if len(customers) > 0 and len(messages) >= 2:
                print("✅ SUCCESS! Webhook is working!")
                print()
                print("🎯 Your setup is correct!")
                print("📱 Real WhatsApp messages will now be saved automatically")
            else:
                print("⚠️  Webhook received but something failed in processing")
                print("👉 Check backend terminal for error logs")
            
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_webhook())
