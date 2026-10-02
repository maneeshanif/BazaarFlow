"""Run every golden case in the fast tier (no network, no API key). A failing case prints what went wrong."""

from __future__ import annotations

from typing import Any

import pytest

from app.evals.harness import Case, check, load_cases, run_case

CASES = load_cases()


@pytest.fixture(autouse=True)
def _no_real_orders(monkeypatch: pytest.MonkeyPatch) -> None:
    """The order tool must never write real data from an evaluation."""

    def fake_save_order(payload: dict[str, Any]) -> dict[str, Any]:
        return {"id": "EVAL-1", "product_name": payload["product_name"], "inventory_snapshot": {}}

    monkeypatch.setattr("app.agents.tools.finance_tool.save_order", fake_save_order)


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
async def test_golden_case(case: Case) -> None:
    outcome = await run_case(case)
    failures = check(case, outcome)
    assert not failures, f"{case.id}: " + "; ".join(failures)
