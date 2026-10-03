"""Check the Twilio WhatsApp sandbox from this machine.

    uv run python -m app.cli.smoke_twilio                                  # credentials only, free, read-only
    uv run python -m app.cli.smoke_twilio --to +923001234567 --body hello  # also sends one sandbox message

Reads TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN from the environment (or .env). Prints a masked sid, never the token.
Exit 0 = every requested check passed.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

import httpx

from app.integrations.twilio_sandbox import (
    BASE_URL,
    SANDBOX_NUMBER,
    TwilioNotConfigured,
    check_account,
    mask,
    send_sandbox_message,
)


async def run(to: str | None, body: str) -> int:
    from dotenv import load_dotenv

    load_dotenv()
    sid, token = os.environ.get("TWILIO_ACCOUNT_SID", ""), os.environ.get("TWILIO_AUTH_TOKEN", "")
    print(f"account sid: {mask(sid)}   sandbox number: {SANDBOX_NUMBER}")
    try:
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            account = await check_account(client, sid, token)
            print(f"{'PASS' if account.ok else 'FAIL'}  credentials: {account.detail}")
            ok = account.ok
            if ok and to:
                sent = await send_sandbox_message(client, sid, token, to=to, body=body)
                print(f"{'PASS' if sent.ok else 'FAIL'}  sandbox message to {to}: {sent.detail}")
                ok = sent.ok
    except TwilioNotConfigured as exc:
        print(f"FAIL  {exc}")
        return 1
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--to", help="E.164 number that has joined the sandbox, e.g. +923001234567")
    parser.add_argument("--body", default="BazaarFlow sandbox check", help="message text")
    args = parser.parse_args(argv)
    return asyncio.run(run(args.to, args.body))


if __name__ == "__main__":
    sys.exit(main())
