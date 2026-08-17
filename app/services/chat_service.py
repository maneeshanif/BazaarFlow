"""Session-aware chat helpers for agent-backed conversations."""
from __future__ import annotations

from typing import Dict, Optional
import logging
import sys

from agents import Runner, SQLiteSession, enable_verbose_stdout_logging

from app.agents.sales_agent import sales_agent
from app.agents.finance_agent import finance_agent
from app.agents.inventory_agent import inventory_agent

logger = logging.getLogger(__name__)

# Emit detailed agent/tool traces to the backend console for easier debugging.
enable_verbose_stdout_logging()

# Pytest swaps sys.stdout with a capture stream, which can be closed at shutdown.
# Nudge the handler added by enable_verbose_stdout_logging() to use the original
# stdout so test runs avoid "I/O operation on closed file" errors.
_agents_logger = logging.getLogger("openai.agents")
for handler in list(_agents_logger.handlers):
    if isinstance(handler, logging.StreamHandler):
        try:
            handler.setStream(sys.__stdout__)
        except AttributeError:  # pragma: no cover - fallback for older Python
            handler.stream = sys.__stdout__


class AgentChatService:
    """Manage chat sessions for a specific agent instance."""

    def __init__(self, *, agent, session_prefix: str) -> None:
        self._agent = agent
        self._session_prefix = session_prefix
        self.active_sessions: Dict[str, SQLiteSession] = {}

    def _resolve_session(self, session_id: Optional[str]) -> tuple[str, SQLiteSession]:
        if not session_id:
            session_id = f"{self._session_prefix}_{len(self.active_sessions) + 1}"

        session = self.active_sessions.get(session_id)
        if session is None:
            session = SQLiteSession(session_id=session_id)
            self.active_sessions[session_id] = session
        return session_id, session

    async def process_message(self, message: str, session_id: Optional[str]) -> tuple[str, str]:
        try:
            resolved_id, session = self._resolve_session(session_id)

            response = await Runner.run(
                starting_agent=self._agent,
                input=message,
                session=session,
            )

            response_text = response.final_output if hasattr(response, "final_output") else str(response)
            return response_text, resolved_id

        except Exception as exc:  # pragma: no cover - defensive path
            logger.error("Error processing message in session %s: %s", session_id, exc)
            return "Sorry, I encountered an error processing your request. Please try again.", (
                session_id or ""
            )

    def get_session(self, session_id: str) -> Optional[SQLiteSession]:
        return self.active_sessions.get(session_id)

    def create_session(self, session_id: str) -> SQLiteSession:
        session = SQLiteSession(session_id=session_id)
        self.active_sessions[session_id] = session
        return session


class ChatService(AgentChatService):
    """Backward-compatible sales chat service."""

    def __init__(self) -> None:
        super().__init__(agent=sales_agent, session_prefix="web")


chat_service = ChatService()
finance_chat_service = AgentChatService(agent=finance_agent, session_prefix="web_finance")
inventory_chat_service = AgentChatService(agent=inventory_agent, session_prefix="web_inventory")