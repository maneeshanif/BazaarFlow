"""Structured logging (build-plan task 57): one JSON object per line in production, readable text in development.

Every record carries the request id of the request that caused it, so a failed request can be followed from the id in
its response (``X-Request-ID`` header and the ``request_id`` of the problem body) to every log line it produced.
Access lines carry method, route, status, duration, tenant and user ids. Nothing else about a request is logged: no
headers, no query string, no body, so tokens, phone numbers and customer names never reach the log.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.request_context import current_request_id
from app.core.settings import settings

EXTRA_FIELDS = ("method", "route", "status", "duration_ms", "tenant_id", "user_id")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = getattr(record, "request_id", None) or current_request_id()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
        }
        for key in EXTRA_FIELDS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


TEXT_FORMAT = "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"


def use_json() -> bool:
    mode = settings.LOG_FORMAT.lower()
    return mode == "json" or (mode == "auto" and settings.APP_ENV in {"production", "staging"})


_factory_installed = False


def _install_record_factory() -> None:
    """Stamp every record, from any logger and any handler, with the id of the request it belongs to."""
    global _factory_installed
    if _factory_installed:
        return
    previous = logging.getLogRecordFactory()

    def factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = previous(*args, **kwargs)
        if getattr(record, "request_id", None) is None:
            record.request_id = current_request_id()
        return record

    logging.setLogRecordFactory(factory)
    _factory_installed = True


def configure_logging() -> None:
    """Idempotent: installs the request-id filter and one stream handler with the chosen format on the root logger."""
    _install_record_factory()
    root = logging.getLogger()
    handler = next((h for h in root.handlers if getattr(h, "_bazaarflow", False)), None)
    if handler is None:
        handler = logging.StreamHandler(sys.stdout)
        handler._bazaarflow = True  # type: ignore[attr-defined]
        root.addHandler(handler)
    handler.setFormatter(JsonFormatter() if use_json() else logging.Formatter(TEXT_FORMAT))
    for existing in list(handler.filters):
        handler.removeFilter(existing)
    handler.addFilter(RequestIdFilter())
    if root.level == logging.NOTSET or root.level > logging.INFO:
        root.setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)  # statements carry values: keep them out of the log
    for name in ("bazaarflow.access", "bazaarflow.error"):
        logging.getLogger(name).disabled = False  # a fileConfig elsewhere in the process must not silence them
    logging.getLogger("uvicorn.access").disabled = True  # our access line replaces it
