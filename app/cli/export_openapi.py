"""Write the API contract (contracts/openapi.json) from the code.

    uv run python -m app.cli.export_openapi          # regenerate
    uv run python -m app.cli.export_openapi --check  # exit 1 if the committed file is stale

The contract is the production surface: the legacy JSON-store routes are left out because they are scheduled
for removal as each module moves onto the tenant-scoped database. The web client types are generated from this
file (``cd frontend && npm run gen:api``); tests/architecture/test_openapi_contract.py fails on drift.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from app.api.routers.main_router import build_main_router
from app.api.routers.v1 import api_v1_router

CONTRACT_PATH = Path(__file__).resolve().parents[2] / "contracts" / "openapi.json"


def build_contract() -> dict[str, Any]:
    api = FastAPI(
        title="BazaarFlow API",
        version="3.0.0",
        description="BazaarFlow - WhatsApp multi-tenant AI sales & marketing platform",
    )
    api.include_router(build_main_router(legacy_routes=False))
    api.include_router(api_v1_router)
    return api.openapi()


def render(spec: dict[str, Any]) -> str:
    return json.dumps(spec, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    text = render(build_contract())
    if "--check" in argv:
        current = CONTRACT_PATH.read_text(encoding="utf-8") if CONTRACT_PATH.exists() else ""
        if current != text:
            print("contracts/openapi.json is stale: run `uv run python -m app.cli.export_openapi`", file=sys.stderr)
            return 1
        print("contract is up to date")
        return 0
    CONTRACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTRACT_PATH.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {CONTRACT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
