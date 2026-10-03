"""Keep personal data out of agent traces (PRD §36.19, build-plan task 65).

Two layers. Patterns catch anything that looks like a phone number or an e-mail address. A per-run ``Redactor`` also
learns the exact personal values the run touched (a customer's name, phone, e-mail, address returned by a tool), and
replaces every occurrence of them, in any casing, so a name that no pattern could recognise is still removed.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.audit import mask_sensitive

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?<![\w.])\+?\d[\d\s\-().]{6,}\d(?![\w])")
_MIN_LEARNED = 2  # a one-letter "name" would blank out ordinary words


class Redactor:
    def __init__(self) -> None:
        self._known: dict[str, str] = {}

    def learn(self, value: str | None, label: str) -> None:
        """Remember a personal value (and its parts, for names) seen during the run."""
        if not value:
            return
        value = value.strip()
        if len(value) >= _MIN_LEARNED:
            self._known.setdefault(value.lower(), f"[{label}]")
        for part in re.split(r"\s+", value):
            if len(part) > 2 and part.lower() not in self._known:
                self._known[part.lower()] = f"[{label}]"

    def text(self, value: str) -> str:
        out = value
        for known in sorted(self._known, key=len, reverse=True):  # longest first: "Zainab Bibi" before "Zainab"
            out = re.sub(re.escape(known), self._known[known], out, flags=re.IGNORECASE)
        out = _EMAIL.sub("[email]", out)
        return _PHONE.sub("[phone]", out)

    def data(self, value: Any) -> Any:
        """Redact every string inside a JSON-like structure, and blank any secret-looking key."""
        value = mask_sensitive(value)
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, dict):
            return {k: self.data(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.data(v) for v in value]
        return value
