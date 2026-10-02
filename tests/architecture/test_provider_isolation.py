"""Task 13 acceptance (PRD §3.7 constraint 11): providers are reached only through the channel adapter layer.

Provider SDK imports and hard-coded provider hosts may appear only in ``app/integrations`` (and in settings, which
holds default base URLs). Legacy modules that still talk to a provider directly are listed in ``LEGACY`` and must
only ever shrink: the phase 2 channel work moves each of them behind an adapter.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"

PROVIDER_PACKAGES = {"pywa", "twilio", "vapi", "facebook", "vonage"}
PROVIDER_HOSTS = re.compile(r"graph\.facebook\.com|api\.twilio\.com|api\.vapi\.ai|graph\.instagram\.com")
ALLOWED_DIRS = ("app/integrations",)
ALLOWED_FILES = {"app/core/settings.py"}  # default base URLs live here
# Legacy direct provider access; each entry needs the phase that removes it. Do not add to this list.
LEGACY: dict[str, str] = {
    "app/services/whatsapp.py": "phase 2: WhatsApp behind the channel adapter (Twilio / Meta)",
    "app/services/vapi_support_service.py": "phase 3: voice behind the channel adapter (VAPI)",
}


def _py_files() -> list[Path]:
    return [p for p in APP.rglob("*.py") if "__pycache__" not in p.parts]


def _rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def _allowed(rel: str) -> bool:
    return rel.startswith(ALLOWED_DIRS) or rel in ALLOWED_FILES or rel in LEGACY


def test_no_provider_sdk_is_imported_outside_the_integrations_layer() -> None:
    offenders = []
    for path in _py_files():
        rel = _rel(path)
        if _allowed(rel):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8", errors="replace"))):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module.split(".")[0]]
            if set(names) & PROVIDER_PACKAGES:
                offenders.append(f"{rel}: imports {sorted(set(names) & PROVIDER_PACKAGES)}")
    assert not offenders, "provider SDK imported outside app/integrations:\n" + "\n".join(offenders)


def test_no_provider_host_is_hard_coded_outside_the_integrations_layer() -> None:
    offenders = [
        _rel(p)
        for p in _py_files()
        if not _allowed(_rel(p)) and PROVIDER_HOSTS.search(p.read_text(encoding="utf-8", errors="replace"))
    ]
    assert not offenders, f"provider host hard-coded outside app/integrations: {offenders}"


def test_the_legacy_list_only_names_files_that_still_need_it() -> None:
    """A legacy entry that no longer touches a provider must be removed, so the list can only shrink."""
    stale = []
    for rel in LEGACY:
        text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
        imports_provider = any(re.search(rf"^\s*(from|import)\s+{pkg}\b", text, re.M) for pkg in PROVIDER_PACKAGES)
        if not imports_provider and not PROVIDER_HOSTS.search(text) and "META_GRAPH" not in text and "VAPI" not in text:
            stale.append(rel)
    assert not stale, f"remove from LEGACY (no direct provider access left): {stale}"
