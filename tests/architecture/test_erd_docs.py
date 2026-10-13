"""docs/erd is generated from the schema. Change a model or a migration without regenerating the diagrams and these fail.

Regenerate with: uv run python docs/erd/generate_erd.py --from-models   (then commit the diff with the migration).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from app.core.database import Base

ERD_DIR = Path(__file__).resolve().parents[2] / "docs" / "erd"


def _generator() -> Any:
    spec = importlib.util.spec_from_file_location("generate_erd", ERD_DIR / "generate_erd.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_table_is_documented_in_exactly_one_context() -> None:
    import app.models  # noqa: F401  (registers every table)

    config = json.loads((ERD_DIR / "erd.config.json").read_text(encoding="utf-8"))
    contexts = [d for d in config["diagrams"] if d["name"] != "Overview"]
    owned: dict[str, list[str]] = {}
    for diagram in contexts:
        for group, tables in diagram["tables"].items():
            if group == "Referenced":  # a table shown only so a link has somewhere to land
                continue
            for table in tables:
                owned.setdefault(table, []).append(diagram["name"])
    missing = sorted(set(Base.metadata.tables) - set(owned))
    twice = sorted(t for t, where in owned.items() if len(where) > 1)
    assert not missing, f"tables with no ERD context in docs/erd/erd.config.json: {missing}"
    assert not twice, f"tables documented as owned by more than one context: {twice}"


def test_the_committed_diagrams_match_the_models() -> None:
    import app.models  # noqa: F401

    expected = _generator().render_all(from_models=True)
    stale = [p.name for p, text in expected.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    assert not stale, (
        f"docs/erd is stale: {stale}. Run: uv run python docs/erd/generate_erd.py --from-models and commit the result"
    )
