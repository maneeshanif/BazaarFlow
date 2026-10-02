"""A model that replays recorded turns, so an agent evaluation runs offline, deterministically and for free.

A *turn* is what the model said once: either some final text or a list of tool calls. The recorded turns of a
golden case are replayed through the real agent loop, so the real instructions-to-tools wiring, tool schemas,
guards and output handling are exercised. (What a replay cannot show is whether the *model* would still choose
the same tool: re-record with ``RecordingModel`` against the live model when the prompt or model changes.)
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from agents import Model, ModelResponse
from agents.usage import Usage
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText


class ReplayExhausted(AssertionError):
    """The agent asked the model for more turns than the case recorded."""


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Turn:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        if self.tool_calls:
            return {"tool_calls": [{"name": c.name, "arguments": c.arguments} for c in self.tool_calls]}
        return {"text": self.text or ""}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Turn:
        if "tool_calls" in data:
            return cls(tool_calls=[ToolCall(c["name"], c.get("arguments", {})) for c in data["tool_calls"]])
        return cls(text=data.get("text", ""))

    def to_output_items(self) -> list[Any]:
        if self.tool_calls:
            return [
                ResponseFunctionToolCall(
                    type="function_call",
                    call_id=f"call_{uuid.uuid4().hex[:12]}",
                    name=c.name,
                    arguments=json.dumps(c.arguments),
                )
                for c in self.tool_calls
            ]
        return [
            ResponseOutputMessage(
                id=f"msg_{uuid.uuid4().hex[:12]}",
                type="message",
                role="assistant",
                status="completed",
                content=[ResponseOutputText(type="output_text", text=self.text or "", annotations=[])],
            )
        ]


class ReplayModel(Model):
    def __init__(self, turns: list[Turn]) -> None:
        self._turns = list(turns)
        self._next = 0

    async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        if self._next >= len(self._turns):
            raise ReplayExhausted(
                f"the agent asked for turn {self._next + 1} but only {len(self._turns)} were recorded"
            )
        turn = self._turns[self._next]
        self._next += 1
        return ModelResponse(output=turn.to_output_items(), usage=Usage(), response_id=f"replay_{self._next}")

    def stream_response(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        raise NotImplementedError("replay models are not streamed")


class RecordingModel(Model):
    """Wraps a live model and captures each reply as a ``Turn`` so a new golden case can be written from it."""

    def __init__(self, inner: Model) -> None:
        self._inner = inner
        self.turns: list[Turn] = []

    async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        response = await self._inner.get_response(*args, **kwargs)
        calls = [
            ToolCall(item.name, json.loads(item.arguments or "{}"))
            for item in response.output
            if isinstance(item, ResponseFunctionToolCall)
        ]
        if calls:
            self.turns.append(Turn(tool_calls=calls))
        else:
            text = "".join(
                part.text
                for item in response.output
                if isinstance(item, ResponseOutputMessage)
                for part in item.content
                if isinstance(part, ResponseOutputText)
            )
            self.turns.append(Turn(text=text))
        return response

    def stream_response(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        raise NotImplementedError("recording models are not streamed")
