from __future__ import annotations

import logging
from typing import Any

from agents.agent import Agent  # type: ignore[import]
from agents.lifecycle import RunHooksBase  # type: ignore[import]
from agents.run_context import RunContextWrapper  # type: ignore[import]


class AgentTurnLogger(RunHooksBase[Any, Agent[Any]]):
    """Run hooks that emit a concise log per agent turn."""

    def __init__(self) -> None:
        self._turn = 0
        self._logger = logging.getLogger("bazaarflow.agent_turns")

    async def on_agent_start(self, context: RunContextWrapper[Any], agent: Agent[Any]) -> None:  # pragma: no cover - glue hook
        self._turn += 1
        self._logger.info(
            "Running agent %s (turn %d)",
            agent.name,
            self._turn,
            extra={
                "agent": agent.name,
                "action": "agent_turn",
                "turn": self._turn,
            },
        )


__all__ = ["AgentTurnLogger"]
