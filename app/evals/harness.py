"""Golden-set evaluation harness for the agents (PRD 36.20; build-plan task 30).

A case = an agent, a customer/owner message, the recorded model turns, and what must be true afterwards. The
harness runs the real agent with a ``ReplayModel`` and checks which tools were called, whether any call is a
write that needs approval, and what the final answer says. It runs in the fast tier: no network, no API key.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agents import Agent, Runner
from agents.items import ToolCallItem

from app.agents.finance_agent import finance_agent
from app.agents.inventory_agent import inventory_agent
from app.agents.sales_agent import sales_agent
from app.agents.tools.manifest import DECLARATIONS
from app.evals.replay import ReplayModel, Turn

GOLDEN_PATH = Path(__file__).resolve().parents[2] / "tests" / "unit" / "evals" / "golden_set.json"

AGENTS: dict[str, Agent[Any]] = {
    "inventory": inventory_agent,
    "finance": finance_agent,
    "sales": sales_agent,
}


@dataclass(frozen=True)
class Expect:
    tools_called: list[str] | None = None  # exact, in order; None = do not check
    tools_not_called: list[str] = field(default_factory=list)
    output_contains: list[str] = field(default_factory=list)
    output_not_contains: list[str] = field(default_factory=list)
    approval_required: list[str] = field(default_factory=list)  # write tools that must have been gated
    raises: str | None = None  # the run is expected to fail with a message containing this
    max_turns: int = 6


@dataclass(frozen=True)
class Case:
    id: str
    agent: str
    input: str
    turns: list[Turn]
    expect: Expect
    note: str = ""


@dataclass
class Outcome:
    tools_called: list[str]
    final_output: str
    approval_required: list[str]
    error: str | None = None


def _approval_gated(tool_names: list[str]) -> list[str]:
    return [n for n in tool_names if (s := DECLARATIONS.get(n)) and s.access == "write" and s.approval != "none"]


async def run_case(case: Case) -> Outcome:
    agent = AGENTS[case.agent].clone(model=ReplayModel(case.turns))
    try:
        result = await Runner.run(agent, case.input, max_turns=case.expect.max_turns)
    except Exception as exc:  # noqa: BLE001 - the harness reports any failure of the run as data
        return Outcome(tools_called=[], final_output="", approval_required=[], error=f"{type(exc).__name__}: {exc}")
    called = [item.raw_item.name for item in result.new_items if isinstance(item, ToolCallItem)]  # type: ignore[union-attr]
    return Outcome(
        tools_called=called,
        final_output=str(result.final_output or ""),
        approval_required=_approval_gated(called),
    )


def check(case: Case, outcome: Outcome) -> list[str]:
    """Human-readable failures; empty means the case passed."""
    exp, failures = case.expect, []
    if outcome.error is not None:
        if exp.raises is None:
            return [f"unexpected error: {outcome.error}"]
        if exp.raises not in outcome.error:
            failures.append(f"expected an error mentioning {exp.raises!r}, got: {outcome.error}")
        return failures
    if exp.raises is not None:
        failures.append(f"expected the run to fail with {exp.raises!r} but it succeeded")
    if exp.tools_called is not None and outcome.tools_called != exp.tools_called:
        failures.append(f"tools called {outcome.tools_called}, expected {exp.tools_called}")
    failures += [f"forbidden tool called: {t}" for t in exp.tools_not_called if t in outcome.tools_called]
    failures += [
        f"output is missing {s!r}: {outcome.final_output!r}"
        for s in exp.output_contains
        if s not in outcome.final_output
    ]
    failures += [f"output must not contain {s!r}" for s in exp.output_not_contains if s in outcome.final_output]
    if sorted(outcome.approval_required) != sorted(exp.approval_required):
        failures.append(f"approval-gated calls {outcome.approval_required}, expected {exp.approval_required}")
    return failures


def load_cases(path: Path = GOLDEN_PATH) -> list[Case]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = []
    for item in raw["cases"]:
        exp = item.get("expect", {})
        cases.append(
            Case(
                id=item["id"],
                agent=item["agent"],
                input=item["input"],
                turns=[Turn.from_dict(t) for t in item["turns"]],
                expect=Expect(
                    tools_called=exp.get("tools_called"),
                    tools_not_called=exp.get("tools_not_called", []),
                    output_contains=exp.get("output_contains", []),
                    output_not_contains=exp.get("output_not_contains", []),
                    approval_required=exp.get("approval_required", []),
                    raises=exp.get("raises"),
                    max_turns=exp.get("max_turns", 6),
                ),
                note=item.get("note", ""),
            )
        )
    return cases
