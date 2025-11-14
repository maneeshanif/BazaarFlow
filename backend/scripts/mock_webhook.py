#!/usr/bin/env python3
"""Send a sample WhatsApp webhook payload to a local FastAPI instance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import httpx  # type: ignore[import-not-found]

SAMPLE_PAYLOAD: Dict[str, Any] = {
    "entry": [
        {
            "changes": [
                {
                    "value": {
                        "metadata": {"phone_number_id": "TEST_PHONE_ID"},
                        "contacts": [
                            {
                                "wa_id": "447700900123",
                                "profile": {"name": "Test Contact"},
                            }
                        ],
                        "messages": [
                            {
                                "from": "447700900123",
                                "id": "wamid.sample",
                                "timestamp": "1700000000",
                                "type": "text",
                                "text": {"body": "Hello from harness"},
                            }
                        ],
                    }
                }
            ]
        }
    ]
}


def load_payload(path: Path | None) -> Dict[str, Any]:
    if not path:
        return SAMPLE_PAYLOAD
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8000/webhook", help="Webhook URL to post to")
    parser.add_argument("--payload", type=Path, help="Optional JSON payload override")
    args = parser.parse_args()

    payload = load_payload(args.payload)
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(args.url, json=payload)
        response.raise_for_status()
        print("Status:", response.status_code)
        print("Body:", response.text)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
