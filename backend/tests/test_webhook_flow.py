"""Test script to simulate a WhatsApp message coming in via webhook."""

import asyncio
import httpx

API_BASE = "http://localhost:8000"

# Sample webhook payload simulating a customer message
SAMPLE_WEBHOOK_PAYLOAD = {
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
                                    "name": "Test Customer"
                                },
                                "wa_id": "923001234567"
                            }
                        ],
                        "messages": [
                            {
                                "from": "923001234567",
                                "id": "wamid.test123",
                                "timestamp": "1699876543",
                                "text": {
                                    "body": "Hi, I want to check product availability"
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
    """Send a test webhook event to the backend."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print("📤 Sending test webhook to backend...")
            response = await client.post(f"{API_BASE}/webhook", json=SAMPLE_WEBHOOK_PAYLOAD)
            print(f"✅ Response status: {response.status_code}")
            print(f"📥 Response body: {response.json()}")
            
            # Now check if customer was created
            print("\n📋 Checking if customer was registered...")
            vendor_id = "d2f0e426-b0ee-4590-88d0-663133267a98"  # From vendors.json
            customers_response = await client.get(f"{API_BASE}/api/vendors/{vendor_id}/customers")
            print(f"👥 Customers: {customers_response.json()}")
            
            # Check messages
            print("\n💬 Checking conversation history...")
            messages_response = await client.get(
                f"{API_BASE}/api/vendors/{vendor_id}/customers/923001234567/messages"
            )
            messages = messages_response.json()
            print(f"📨 Messages count: {len(messages.get('messages', []))}")
            for msg in messages.get('messages', []):
                direction = msg.get('direction')
                text = msg.get('text', '(no text)')
                print(f"  {direction}: {text}")
            
        except httpx.HTTPError as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("🧪 Testing WhatsApp Webhook Flow\n")
    print("Make sure backend is running on http://localhost:8000\n")
    asyncio.run(test_webhook())
