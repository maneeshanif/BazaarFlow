"""Task 25: the API contract is a committed file, the web client types are generated from it, and both are
checked for drift. Change an endpoint without regenerating and these tests fail (verify.sh also runs them)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.cli.export_openapi import build_contract, render

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "openapi.json"
TS_TYPES = ROOT / "frontend" / "lib" / "api" / "schema.d.ts"


def test_committed_contract_matches_the_code() -> None:
    assert CONTRACT.exists(), "run: uv run python -m app.cli.export_openapi"
    assert CONTRACT.read_text(encoding="utf-8") == render(build_contract()), (
        "contracts/openapi.json is stale. Regenerate it: uv run python -m app.cli.export_openapi "
        "(then: cd frontend && npm run gen:api)"
    )


def test_contract_is_the_production_surface_not_the_legacy_routes() -> None:
    paths = build_contract()["paths"]
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/customers/" in paths
    legacy = [p for p in paths if p.startswith(("/api/inventory", "/api/sales", "/api/vendors", "/api/logs"))]
    assert legacy == [], f"legacy JSON-store routes must not be in the contract: {legacy}"


def test_every_operation_is_documented_enough_to_generate_a_client() -> None:
    spec = build_contract()
    operation_ids: list[str] = []
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            assert op.get("operationId"), f"{method.upper()} {path} has no operationId"
            assert op.get("responses"), f"{method.upper()} {path} declares no responses"
            operation_ids.append(op["operationId"])
    assert len(operation_ids) == len(set(operation_ids)), "operationIds must be unique"


def test_contract_output_is_deterministic() -> None:
    assert render(build_contract()) == render(build_contract())
    assert json.loads(render(build_contract())) == build_contract()


def test_generated_client_types_exist_and_cover_every_path() -> None:
    assert TS_TYPES.exists(), "run: cd frontend && npm run gen:api"
    text = TS_TYPES.read_text(encoding="utf-8")
    missing = [p for p in build_contract()["paths"] if f'"{p}"' not in text]
    assert missing == [], (
        f"frontend/lib/api/schema.d.ts is stale; missing {missing}. Run: cd frontend && npm run gen:api"
    )


@pytest.mark.skipif(not (ROOT / "frontend" / "node_modules" / ".bin").exists(), reason="web dependencies not installed")
def test_generated_client_types_are_byte_identical_to_a_fresh_generation(tmp_path: Path) -> None:
    out = tmp_path / "schema.d.ts"
    npx = "npx.cmd" if sys.platform == "win32" else "npx"
    subprocess.run(
        [npx, "openapi-typescript", str(CONTRACT), "-o", str(out)],
        cwd=ROOT / "frontend",
        check=True,
        capture_output=True,
    )
    assert out.read_text(encoding="utf-8").replace("\r\n", "\n") == TS_TYPES.read_text(encoding="utf-8").replace(
        "\r\n", "\n"
    ), "frontend/lib/api/schema.d.ts is stale. Run: cd frontend && npm run gen:api"
