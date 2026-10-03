"""Task 12: every variable the code reads is documented, and the proposed .env.example lists them all, empty."""

from __future__ import annotations

import re
from pathlib import Path

from agent_service.settings import AgentServiceSettings
from app.core.settings import Settings

ROOT = Path(__file__).resolve().parents[2]
DOC = (ROOT / "docs" / "operations" / "env-vars.md").read_text(encoding="utf-8")
PROPOSED = (ROOT / "docs" / "operations" / "env.example.proposed").read_text(encoding="utf-8")


def _documented() -> set[str]:
    names: set[str] = set()
    for line in DOC.splitlines():
        if line.startswith("| `"):
            names.update(re.findall(r"`([A-Z][A-Z0-9_]+)`", line.split("|")[1]))
    return names


def test_every_api_and_agent_service_setting_is_documented() -> None:
    fields = set(Settings.model_fields) | set(AgentServiceSettings.model_fields)
    missing = sorted(fields - _documented())
    assert not missing, f"add these to docs/operations/env-vars.md: {missing}"


def test_the_proposed_env_example_lists_every_documented_variable_with_an_empty_value() -> None:
    entries = dict(line.split("=", 1) for line in PROPOSED.splitlines() if line and not line.startswith("#"))
    assert set(entries) == _documented()
    assert all(value == "" for value in entries.values()), "an .env.example value must be empty"


def test_no_secret_looking_value_is_written_in_the_docs() -> None:
    suspicious = re.findall(r"(?:sk-|AIza|EAA|xox[bp]-)[A-Za-z0-9_-]{10,}", DOC + PROPOSED)
    assert suspicious == []
