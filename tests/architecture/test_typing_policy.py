"""Task 16 acceptance: strict mypy applies to everything, with no per-module escape hatch.

A module that is not strict-clean must be fixed, not listed. The only override allowed is for a third-party
package that publishes no type stubs.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

PYPROJECT = tomllib.loads((Path(__file__).resolve().parents[2] / "pyproject.toml").read_text(encoding="utf-8"))
MYPY = PYPROJECT["tool"]["mypy"]


def test_mypy_is_strict() -> None:
    assert MYPY["strict"] is True


def test_no_module_is_exempted_from_type_errors() -> None:
    overrides = MYPY.get("overrides", [])
    offenders = [o["module"] for o in overrides if o.get("ignore_errors")]
    assert not offenders, f"ignore_errors overrides are not allowed, fix the modules instead: {offenders}"


def test_the_only_overrides_are_for_packages_without_stubs() -> None:
    for override in MYPY.get("overrides", []):
        modules = override["module"] if isinstance(override["module"], list) else [override["module"]]
        assert set(override) <= {"module", "ignore_missing_imports"}, override
        assert override.get("ignore_missing_imports") is True, override
        assert all(m.split(".")[0] in {"asyncpg"} for m in modules), f"unexpected override for {modules}"
