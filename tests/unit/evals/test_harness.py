"""Task 30: the evaluation harness itself. A golden case replays recorded model turns through the real agent,
real tools and real SDK loop, and checks what the agent did (tools, approval, output). These tests prove the
harness catches regressions, using small in-test cases."""

from __future__ import annotations

from typing import Any

import pytest

from app.evals.harness import Case, Expect, Outcome, check, load_cases, run_case
from app.evals.replay import RecordingModel, ReplayExhausted, ReplayModel, ToolCall, Turn


def _case(turns: list[Turn], expect: Expect, *, agent: str = "inventory", text: str = "show phones") -> Case:
    return Case(id="t", agent=agent, input=text, turns=turns, expect=expect)


async def test_a_case_that_calls_the_expected_tool_passes() -> None:
    case = _case(
        [Turn(tool_calls=[ToolCall("inventory_search_items", {"query": "phone"})]), Turn(text="Here are phones")],
        Expect(tools_called=["inventory_search_items"], output_contains=["phones"]),
    )
    outcome = await run_case(case)
    assert outcome.tools_called == ["inventory_search_items"]
    assert outcome.final_output == "Here are phones"
    assert check(case, outcome) == []


async def test_the_wrong_tool_is_reported() -> None:
    case = _case(
        [Turn(tool_calls=[ToolCall("inventory_stock_overview", {})]), Turn(text="ok")],
        Expect(tools_called=["inventory_search_items"]),
    )
    failures = check(case, await run_case(case))
    assert failures and "inventory_search_items" in failures[0]


async def test_a_forbidden_tool_and_forbidden_text_are_reported() -> None:
    case = _case(
        [Turn(tool_calls=[ToolCall("inventory_stock_overview", {})]), Turn(text="we have 12 units left")],
        Expect(tools_not_called=["inventory_stock_overview"], output_not_contains=["units left"]),
    )
    failures = check(case, await run_case(case))
    assert len(failures) == 2


async def test_a_write_tool_is_flagged_as_needing_approval() -> None:
    args = {
        "customer_name": "Ali",
        "customer_phone": "+923001234567",
        "product_name": "Phone",
        "quantity": 1,
        "delivery_address": "Lahore",
    }
    case = _case(
        [Turn(tool_calls=[ToolCall("create_customer_order", args)]), Turn(text="placed")],
        Expect(tools_called=["create_customer_order"], approval_required=["create_customer_order"]),
        agent="finance",
        text="I want to order a phone",
    )
    outcome = await run_case(case)
    assert outcome.approval_required == ["create_customer_order"]
    assert check(case, outcome) == []


async def test_a_model_that_invents_a_tool_fails_the_run_and_can_be_expected_to() -> None:
    turns = [Turn(tool_calls=[ToolCall("delete_all_customers", {})]), Turn(text="done")]
    outcome = await run_case(_case(turns, Expect()))
    assert outcome.error is not None
    assert check(_case(turns, Expect()), outcome), "an unexpected error is a failure"
    expecting_error = _case(turns, Expect(raises="delete_all_customers"))
    assert check(expecting_error, await run_case(expecting_error)) == []


async def test_a_greeting_must_not_call_any_tool() -> None:
    case = _case(
        [Turn(text="Hi! What can I show you?")],
        Expect(tools_called=[], output_contains=["Hi"]),
        agent="sales",
        text="hello",
    )
    assert check(case, await run_case(case)) == []


async def test_replay_fails_loudly_when_the_agent_asks_for_more_turns_than_were_recorded() -> None:
    model = ReplayModel([Turn(text="one")])
    await model.get_response(
        "", "x", None, [], None, [], None, previous_response_id=None, conversation_id=None, prompt=None
    )
    with pytest.raises(ReplayExhausted):
        await model.get_response(
            "", "x", None, [], None, [], None, previous_response_id=None, conversation_id=None, prompt=None
        )


async def test_recording_model_captures_turns_in_the_replay_format() -> None:
    inner = ReplayModel([Turn(tool_calls=[ToolCall("inventory_stock_overview", {})]), Turn(text="done")])
    recorder = RecordingModel(inner)
    from agents import Agent, Runner

    agent = Agent(name="x", instructions="x", model=recorder, tools=[])
    # the recorded inner model asks for a tool the bare agent does not have; only the capture matters here
    with pytest.raises(Exception):  # noqa: B017, PT011
        await Runner.run(agent, "hi", max_turns=2)
    assert recorder.turns[0].tool_calls[0].name == "inventory_stock_overview"


def test_turns_round_trip_through_json() -> None:
    turn = Turn(tool_calls=[ToolCall("inventory_search_items", {"query": "x"})])
    assert Turn.from_dict(turn.to_dict()) == turn
    assert Turn.from_dict(Turn(text="hi").to_dict()) == Turn(text="hi")


def test_the_golden_set_loads_and_is_not_trivially_small() -> None:
    cases = load_cases()
    assert len(cases) >= 10
    assert len({c.id for c in cases}) == len(cases), "case ids must be unique"


def _unused(_: Any, __: Outcome) -> None: ...
