from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Deque, Dict, List


class LiveLogBuffer:
    """Thread-safe ring buffer for recent log records."""

    def __init__(self, capacity: int = 200) -> None:
        self._entries: Deque[Dict[str, Any]] = deque(maxlen=capacity)
        self._lock = Lock()

    def append(self, entry: Dict[str, Any]) -> None:
        with self._lock:
            self._entries.append(entry)

    def snapshot(self, limit: int | None = None) -> List[Dict[str, Any]]:
        with self._lock:
            data = list(self._entries)
        if limit is not None:
            return data[-limit:]
        return data


_buffer = LiveLogBuffer()


class LiveLogHandler(logging.Handler):
    """Logging handler that mirrors log records into an in-memory buffer."""

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - trivial
        try:
            payload = {
                "id": f"{record.created:.3f}-{record.msecs:.0f}",
                "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
                "level": record.levelname.lower(),
                "logger": record.name,
                "message": record.getMessage(),
            }
            for key in ("agent", "action", "status", "tool", "turn"):
                value = getattr(record, key, None)
                if value is not None:
                    payload[key] = value
            _buffer.append(payload)
        except Exception:
            self.handleError(record)


def configure_live_logging(level: int = logging.INFO) -> None:
    """Attach the live log handler to the root logger if not already present."""

    root = logging.getLogger()
    root.setLevel(min(root.level, level) if root.handlers else level)
    for handler in root.handlers:
        if isinstance(handler, LiveLogHandler):
            live_handler = handler
            break
    else:
        live_handler = LiveLogHandler()
        root.addHandler(live_handler)
    live_handler.setLevel(logging.NOTSET)

    agents_logger = logging.getLogger("openai.agents")
    agents_logger.propagate = True


def get_recent_logs(
    limit: int = 100,
    action: str | None = None,
    logger_name: str | None = None,
) -> List[Dict[str, Any]]:
    entries = _buffer.snapshot()
    if action:
        entries = [entry for entry in entries if entry.get("action") == action]
    if logger_name:
        prefix = f"{logger_name}."
        entries = [
            entry
            for entry in entries
            if entry.get("logger") == logger_name or str(entry.get("logger", "")).startswith(prefix)
        ]
    if limit:
        entries = entries[-limit:]
    return list(reversed(entries))
