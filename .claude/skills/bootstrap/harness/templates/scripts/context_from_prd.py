#!/usr/bin/env python3
"""
Generate the PRD-derived context files from a PRD written with the `prd` skill (38-section template).

    python3 context_from_prd.py docs/prd/PRD.md --out context [--files overview,architecture,build-plan,progress-tracker]
                                [--phase0-extra "task text"]... [--skip-task audit,tenancy] [--no-mock-first] [--force]

Creates (never overwrites an existing file unless --force):
  project-overview.md   about, objectives, modules and screens, priorities, constraints, deployment, definition of done
  architecture.md       stack, deferred tech, deployment units, folder structure, tenancy, security, audit, offline,
                        AI architecture, database conventions/domains, API surface, performance targets
  build-plan.md         core principle, phase map, and numbered tasks per phase (Phase 0 foundation tasks are derived
                        from the PRD `features`; later tasks come from the form/dashboard/integration registers)
  progress-tracker.md   current status + one checklist per phase (all tasks unchecked)

Everything comes from the PRD; text is copied, tables are copied, IDs are preserved. Sections marked
"Not applicable" are skipped. Customise with the flags above, or edit the generated files by hand (they are living documents).
Standard library only.
"""
import argparse
import difflib
import re
import sys
from pathlib import Path

ALL_FILES = ["overview", "architecture", "build-plan", "progress-tracker", "progress-log"]

MAX_TASK_ACCEPTANCE = 6  # a task needing more than this cannot be verified in one fast-tier cycle: split it

FOUNDATION_ACCEPT: dict[str, list[str]] = {
    "adr": ["`docs/adr/0001-stack-decision.md` exists and names the stack, the reasons and the rejected alternatives", "The developer has signed it off (recorded in the progress log)"],
    "scaffold": ["Every folder in PRD §3.4 exists and each part builds or runs an empty smoke test", "`.env.example` lists every variable with an empty value; no real secret is committed"],
    "ci": ["Every lane has a workflow that calls `scripts/verify.sh`; a deliberately broken commit turns CI red", "Secret scan and dependency scan run and pass on the clean tree"],
    "database": ["The first migration applies to an empty database and the migration check in `verify.sh` passes", "Table, column and key names follow PRD §12.2"],
    "auth": ["Login, refresh and logout work; a wrong password and an expired token are rejected", "A user without the role gets 403 on a protected endpoint (test per role in PRD §14.2)"],
    "tenancy": ["A test proves tenant A cannot read or write tenant B's rows", "A request with no tenant context returns zero rows (deny by default)"],
    "audit": ["Each audited action in PRD §14.1 writes exactly one audit row (one test per action)", "Sensitive fields are masked in the stored row"],
    "contract": ["The generated client matches the live OpenAPI document; the drift check passes", "Errors use the documented error format"],
    "ui": ["Design tokens are the only source of colour, type and spacing; a lint or grep check finds no hard-coded values", "The layout shell renders at mobile and desktop widths without horizontal scroll"],
    "agents": ["The agent service has no database credentials in its environment", "A tool call reaches the API with the caller's identity, and a forbidden call is rejected"],
    "slice": ["The smallest feature works end to end across every layer with one automated test", "`scripts/verify.sh` passes and the pattern is written down for later tasks to copy"],
}

LADDER = """## Production MVP and the Infrastructure Ladder

Phase 0 and Phase 1 are a **production MVP**: the smallest thing real users can rely on. Do not build for scale that has not arrived. Start at step 1 and move up only when the stated trigger is true and measured.

| Step | Setup | Move up when |
| --- | --- | --- |
| 1 | Free tiers: one managed host, one managed database, free error tracking and uptime check | Free-tier limits are reached or the uptime check shows repeated failures |
| 2 | Paid small instances, automated backups, staging environment, secrets in a manager | Paying users exist, or an outage would cost money |
| 3 | Autoscaling or multiple instances, read replicas or caching, structured logs and alerts | p95 latency or CPU stays above the PRD §17 target for a week |
| 4 | Multi-region, queues and workers, formal on-call and DR drills | A written availability or compliance requirement the lower steps cannot meet |

Anything the PRD wants beyond the MVP goes in a later phase with its trigger written next to it.

"""


# ------------------------------------------------------------------ parsing
def split_front_matter(text: str) -> tuple[dict, str]:
    text = re.sub(r"^<!--.*?-->\s*", "", text, flags=re.S)
    m = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not m:
        return {}, text
    fm: dict = {}
    key = None
    for raw in m.group(1).splitlines():
        line = raw.split("  #")[0].rstrip()
        if not line.strip():
            continue
        if re.match(r"^\S", line):
            k, _, v = line.partition(":")
            key, v = k.strip(), v.strip().strip('"')
            fm[key] = v if v else ([] if key == "features" else {})
        elif isinstance(fm.get(key), dict):
            k, _, v = line.strip().partition(":")
            fm[key][k.strip()] = v.strip().strip('"')
        elif line.lstrip().startswith("-") and isinstance(fm.get(key), list):
            fm[key].append(line.lstrip()[1:].strip().strip('"'))
    if isinstance(fm.get("features"), str):
        fm["features"] = [x.strip().strip('"') for x in fm["features"].strip("[] ").split(",") if x.strip()]
    return fm, text[m.end():]


class Prd:
    def __init__(self, path: Path) -> None:
        self.fm, self.body = split_front_matter(path.read_text(encoding="utf-8"))
        self.body = re.sub(r"<!--.*?-->", "", self.body, flags=re.S)
        self.lines = self.body.splitlines()

    def _grab(self, pattern: str, stop: str) -> str:
        start = next((i for i, l in enumerate(self.lines) if re.match(pattern, l)), None)
        if start is None:
            return ""
        end = next((j for j in range(start + 1, len(self.lines)) if re.match(stop, self.lines[j])), len(self.lines))
        return "\n".join(self.lines[start + 1:end]).strip()

    def sec(self, n: int) -> str:
        """whole section n including its subsections"""
        return self._grab(rf"^## {n}\. ", r"^## \d+\. |^## Appendix|^---\s*$")

    def sub(self, n: str) -> str:
        """subsection like '3.7' (body only)"""
        return self._grab(rf"^###+ {re.escape(n)}[ .]", r"^#{2,3} ")

    def title(self) -> str:
        return self.fm.get("project") or next((re.sub(r"^#\s+", "", l) for l in self.lines if l.startswith("# ")), "Project")


def real(text: str) -> bool:
    """True when the text carries content (not empty, not 'Not applicable', not only italic guidance)."""
    t = text.strip()
    if not t or re.match(r"(?i)^not applicable", t):
        return False
    body = [l for l in t.splitlines() if l.strip() and not re.match(r"^_.*_$", l.strip()) and not re.match(r"^\|[\s:|-]+\|$", l.strip())]
    if not body:
        return False
    # a table with only a header row and empty cells is not content
    if all(l.strip().startswith("|") for l in body):
        cells = [c.strip() for l in body[1:] for c in l.strip().strip("|").split("|")]
        return any(cells)
    return True


def table_rows(text: str) -> list[list[str]]:
    rows = []
    for l in text.splitlines():
        if l.strip().startswith("|") and not re.match(r"^\s*\|[\s:|-]+\|\s*$", l):
            rows.append([c.strip() for c in l.strip().strip("|").split("|")])
    return rows


def first_int(s: str) -> int | None:
    m = re.match(r"^\D*(\d+)", s.strip())
    return int(m.group(1)) if m else None


# ------------------------------------------------------------------ files
def header(prd: Prd, name: str, prd_path: str) -> str:
    return (f"# {name}\n\n> Generated from `{prd_path}` (v{prd.fm.get('version', '?')}, profile `{prd.fm.get('profile', '?')}`) by "
            "Honey's Spec Harness. This is a living document: edit it freely; the PRD stays the source for scope.\n\n")


def block(title: str, text: str, missing_note: str = "") -> str:
    if real(text):
        return f"## {title}\n\n{text.strip()}\n\n"
    return f"## {title}\n\n_{missing_note or 'Not specified in the PRD yet. See Open Questions in context/progress-tracker.md.'}_\n\n"


def overview(prd: Prd, prd_path: str, warns: list[str]) -> str:
    out = header(prd, "Project Overview", prd_path)
    out += block("About the Project", prd.sec(1))
    out += block("Product Objectives", prd.sec(2))
    mods = prd.sec(27)
    if not real(mods):
        reg = table_rows(prd.sub("5.2"))
        if len(reg) > 1:
            by: dict[str, list[str]] = {}
            for r in reg[1:]:
                if len(r) >= 3 and r[0]:
                    by.setdefault(r[2] or "General", []).append(f"{r[0]} {r[1]}")
            mods = "| Module | Screens |\n| --- | --- |\n" + "\n".join(f"| {m} | {'; '.join(v)} |" for m, v in by.items())
    out += block("Modules & Primary Screens", mods)
    out += block("Feature Priority", prd.sec(26))
    out += block("Non-Negotiable Architectural Constraints", prd.sub("3.7"))
    out += block("Deployment Models", prd.sub("3.6"))
    out += block("Definition of Done", prd.sec(24))
    if not real(prd.sec(1)):
        warns.append("PRD section 1 (Executive Summary) is empty")
    return out


def architecture(prd: Prd, prd_path: str, warns: list[str]) -> str:
    feats = set(prd.fm.get("features", []))
    out = header(prd, "Architecture", prd_path)
    out += block("Stack", prd.sub("3.1"))
    if real(prd.sub("3.2")):
        out += block("Considered and Deferred", prd.sub("3.2"))
    out += block("Deployment Units", prd.sub("3.3"))
    folder = prd.sub("3.4")
    if not real(folder) and isinstance(prd.fm.get("layout"), dict):
        folder = "```\n" + "\n".join(f"{v}/    # {k}" for k, v in prd.fm["layout"].items()) + "\n```"
    out += block("Folder Structure", folder)
    if "tenancy" in feats or real(prd.sub("3.5")):
        out += block("Multi-Tenancy & Scoping", prd.sub("3.5"))
    sec14 = prd.sec(14)
    out += block("Security, Authentication & Authorization", sec14)
    if "audit" in feats and real(prd.sub("14.1")):
        out += block("Audit Architecture", prd.sub("14.1"))
    if real(prd.sec(11)):
        out += block("Offline & Sync", prd.sec(11))
    if "ai-agents" in feats and real(prd.sec(36)):
        out += block("Agentic AI Architecture", prd.sec(36))
    if real(prd.sec(12)):
        out += block("Database Conventions & Domains", prd.sec(12))
    if real(prd.sec(13)):
        out += block("API Surface", prd.sec(13))
    out += block("Performance Targets", prd.sec(17))
    if real(prd.sec(18)):
        out += block("Backup & Disaster Recovery", prd.sec(18))
    return out


# ---- build plan
def foundation_tasks(prd: Prd, skip: set[str], extra: list[str]) -> list[tuple[str, str]]:
    feats = set(prd.fm.get("features", []))
    layout = prd.fm.get("layout", {}) if isinstance(prd.fm.get("layout"), dict) else {}
    stack = prd.fm.get("stack", {}) if isinstance(prd.fm.get("stack"), dict) else {}
    lanes = ", ".join(layout.keys()) or "the chosen parts"
    t: list[tuple[str, str]] = [
        ("adr", "Architecture Decision Record + sign-off — write `docs/adr/0001-stack-decision.md` from PRD §3.1 (stack, why, rejected alternatives)"),
        ("scaffold", f"Repo scaffold — folders per PRD §3.4 ({', '.join(f'`{v}`' for v in layout.values()) or 'as designed'}), package managers, `.env.example` with empty values"),
        ("ci", f"CI/CD + verification — one workflow per lane ({lanes}) calling `scripts/verify.sh`; secret scan; dependency scan"),
    ]
    if "database" in feats:
        t.append(("database", f"Database foundation — {stack.get('database', 'database')} + {stack.get('migrations', 'migrations')}; first migration; naming and key conventions from PRD §12.2; migration check in `verify.sh`"))
    t.append(("auth", "Authentication & authorization — login/refresh/logout, roles and permission matrix from PRD §14.2, enforced in the API"))
    if "tenancy" in feats:
        t.append(("tenancy", "Tenancy enforcement — central scoping filter, deny-by-default, cross-tenant access tests (PRD §3.5)"))
    if "audit" in feats:
        t.append(("audit", "Audit infrastructure — audit rows for the actions in PRD §14.1, sensitive-field masking, test that each audited action writes a row"))
    if "api-contract" in feats:
        t.append(("contract", f"API conventions + contract — versioned base path, error format, OpenAPI, generated client ({stack.get('api_contract', 'openapi')}), drift check in `verify.sh`"))
    if "ui" in feats:
        t.append(("ui", "UI foundation — design tokens, layout shell, the mandated form layout (PRD §5.1), reusable grid/form/status components, `context/ui-registry.md` started"))
    if "ai-agents" in feats:
        t.append(("agents", "Agent service skeleton — separate service, no database credentials, tool catalog wired to the API with the caller's identity (PRD §36.2-36.4)"))
    t.append(("slice", "Vertical slice — the smallest end-to-end feature across every layer, to prove the pattern later tasks copy"))
    return [(k, v) for k, v in t if k not in skip] + [("extra", e) for e in extra]


def find_packs_dir(explicit: str) -> Path | None:
    """The packs/ folder: --packs-dir, else next to the harness (repo checkout or the bootstrap bundle)."""
    here = Path(__file__).resolve()
    for c in ([Path(explicit)] if explicit else []) + [here.parents[2] / "packs", here.parents[1] / "packs", Path("packs")]:
        if c.is_dir():
            return c
    return None


def pack_material(packs_dir: Path | None, wanted: list[str], warns: list[str]):
    """-> (tasks_by_phase {0:[(text, acc)],1:[...]}, checklist [(id, text, pack)], deferred [(item, trigger, pack)])"""
    tasks: dict[int, list] = {0: [], 1: []}
    checklist: list = []
    deferred: list = []
    for pid in wanted:
        d = packs_dir / pid if packs_dir else None
        if not d or not (d / "phases.md").is_file():
            warns.append(f"pack '{pid}' not found; skipped")
            continue
        text = (d / "phases.md").read_text(encoding="utf-8")
        sect = None
        for line in text.splitlines():
            m = re.match(r"^## (Phase (\d)|Deferred)", line)
            if m:
                sect = m.group(2) if m.group(2) else "deferred"
            elif sect and line.startswith("- "):
                if sect == "deferred":
                    a, _, b = line[2:].partition(" — Trigger: ")
                    deferred.append((a.strip(), b.strip(), pid))
                else:
                    a, _, b = line[2:].partition(" — Accept: ")
                    tasks[int(sect)].append((f"{a.strip()} [{pid} pack]", [x.strip() for x in re.split(r";\s+", b.strip()) if x.strip()]))
        if (d / "checklist.md").is_file():
            for cid, ctext in re.findall(r"^- \[ \] (C-[A-Z0-9]+-\d{2}) (.+)$", (d / "checklist.md").read_text(encoding="utf-8"), re.M):
                checklist.append((cid, ctext, pid))
    return tasks, checklist, deferred


def accept_for(key: str) -> list[str]:
    return FOUNDATION_ACCEPT.get(key, ["The done-condition for this task is written here and has an automated check"])


def build_plan(prd: Prd, prd_path: str, args: argparse.Namespace, warns: list[str]) -> tuple[str, list[tuple[str, list[str]]]]:
    feats = set(prd.fm.get("features", []))
    skip = {s.strip() for s in args.skip_task.split(",") if s.strip()}
    phases = [r for r in table_rows(prd.sec(22))[1:] if r and first_int(r[0]) is not None]
    if not phases:
        warns.append("PRD section 22 has no phase rows; wrote a single Phase 0 only")
        phases = [["0", "Foundation", "Foundation approved + CI green + login works"]]
    if not any(first_int(r[0]) == 0 for r in phases):
        phases.insert(0, ["0", "Foundation: repo, CI, migrations, auth, tenancy/audit skeleton, design tokens", "Foundation approved + CI green + login works end to end"])

    pack_names = [x.strip() for x in args.packs.split(",") if x.strip()]
    pack_tasks, pack_checklist, pack_deferred = pack_material(find_packs_dir(args.packs_dir), pack_names, warns)
    forms = table_rows(prd.sub("5.2"))[1:]
    dashes = table_rows(prd.sec(7))[1:]
    integs = table_rows(prd.sub("13.3"))[1:]
    n = 0
    plan: list[tuple[str, list[str]]] = []
    text = header(prd, "Build Plan", prd_path)
    mock = ("Full-page UI built with mock data first and verified visually before any logic is written; then functionality is wired step by step. "
            "Every feature is visible and testable before the next one starts. No invisible backend phases.") if ("ui" in feats and not args.no_mock_first) else \
           "Vertical slices: each task delivers something runnable and testable end to end before the next one starts."
    text += f"## Core Principle\n\n{mock}\n\nEvery task cites its **feature ID** (F-, D-, R-, W-, I-xxx) or PRD section. Never invent a business field that is not in the PRD (PRD §5.3); record a change request first (PRD §25).\n\n"
    text += "## Phase Map\n\n| Phase | Scope | Exit Criteria |\n| --- | --- | --- |\n"
    for r in phases:
        text += f"| {r[0]} | {r[1] if len(r) > 1 else ''} | {r[2] if len(r) > 2 else ''} |\n"
    text += "\n" + LADDER
    text += ("## Task Size Rule\n\nA task must be verifiable in one fast-tier cycle (`bash scripts/verify.sh`, seconds). If its acceptance criteria need more than "
             f"{MAX_TASK_ACCEPTANCE} checks, or any check needs the slow tier to prove the basic behaviour, split the task before starting it. "
             "`python3 scripts/check_plan.py` flags oversized tasks, duplicates, tasks without acceptance criteria, and a tracker that disagrees with this plan.\n\n")
    text += "---\n\n"
    for r in phases:
        pn = first_int(r[0]) or 0
        text += f"## Phase {pn} — {r[1] if len(r) > 1 else ''}\n\nExit gate: {r[2] if len(r) > 2 else '(define in PRD §22)'}\n\n"
        items: list[str] = []
        if pn == 0:
            for key, desc in foundation_tasks(prd, skip, args.phase0_extra):
                items.append((desc, accept_for(key)))
        for f in forms:
            if len(f) >= 7 and first_int(f[6]) == pn and re.match(r"^F-\d+", f[0]):
                items.append((f"{f[1]} — {f[0]} ({f[2]}; {f[3]}; {f[5]}; roles: {f[4]})", [
                    f"A user with one of the roles ({f[4]}) can complete the {f[2]} flow; a user without them gets 403",
                    f"Validation and required fields match the field spec for {f[0]} in PRD §5.3 (one test per rule)",
                    "One end-to-end test drives the form and checks what was stored"]))
        for d in dashes:
            if len(d) >= 6 and first_int(d[5]) == pn and re.match(r"^D-\d+", d[0]):
                items.append((f"{d[1]} dashboard — {d[0]} (role: {d[2]}; KPIs: {d[3]})", [
                    f"Each KPI ({d[3]}) matches a hand-computed value on a seeded dataset",
                    f"Only role {d[2]} can open it; an empty dataset shows an empty state, not an error"]))
        for it in integs:
            if len(it) >= 7 and first_int(it[6]) == pn and re.match(r"^I-\d+", it[0]):
                items.append((f"Integration: {it[1]} — {it[0]} ({it[2]}; {it[3]})", [
                    "A contract test against a recorded or sandbox response proves the happy path",
                    "A timeout, an error response and a duplicate delivery are each handled by a test"]))
        have = [normalize_task(t) for t, _ in items]
        for ptext, pacc in pack_tasks.get(pn, []):
            if any(difflib.SequenceMatcher(None, normalize_task(ptext), h).ratio() >= 0.6 for h in have):
                continue  # the foundation already covers it; do not duplicate
            items.append((ptext, pacc))
        if not items and pn != 0:
            items.append(("(no forms, dashboards or integrations are assigned to this phase in the PRD registers — assign them in PRD §5.2 / §7 / §13.3 or add tasks here)", ["Assign registered items to this phase, then regenerate"]))
            warns.append(f"phase {pn} has no registered items")
        numbered = []
        for it, acc in items:
            numbered.append(f"{n:02d} {it}")
            text += f"- [ ] {n:02d} {it}\n"
            for a_ in acc[:MAX_TASK_ACCEPTANCE]:
                text += f"  - Acceptance: {a_}\n"
            n += 1
        text += "\nEach task: confirm the acceptance criteria (`/architect` turns them into failing tests first), then build, then `bash scripts/verify.sh`, then `/review`.\n\n"
        plan.append((f"Phase {pn} — {r[1] if len(r) > 1 else ''}", numbered))
    if pack_checklist:
        text += "## Pack Checklists — answer before Phase 1 exits\n\nEach item becomes a PRD requirement and a candidate acceptance test. Tick it here when the PRD answers it.\n\n"
        for cid, ctext, pid in pack_checklist:
            text += f"- [ ] {cid} {ctext} ({pid})\n"
        text += "\n"
    if pack_deferred:
        text += "## Deferred — with the trigger that brings each back\n\n| Item | Trigger | Pack |\n| --- | --- | --- |\n"
        for item, trig, pid in pack_deferred:
            text += f"| {item} | {trig} | {pid} |\n"
        text += "\n"
    return text, plan


def normalize_task(t: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", re.sub(r"\(.*?\)|\[.*?\]", " ", t.lower()))


def short_title(item: str, limit: int = 70) -> str:
    """'03 Title — detail' -> '03 Title' (the build plan keeps the detail)."""
    head = item.split(" — ")[0].strip()
    return head if len(head) <= limit else head[: limit - 1].rstrip() + "…"


PROGRESS_LOG = """# Progress Log

Append-only history. Never edit or delete a line. The short status lives in `progress-tracker.md`; this file is where finished work, decisions and rulings are recorded, one dated line each, newest at the bottom. Agents read the tracker every session and this log only when they need history.

<!-- one line per event: YYYY-MM-DD — task NN done | decision | ruling — what and why -->
"""


def tracker(prd: Prd, plan: list[tuple[str, list[str]]], template: Path | None) -> str:
    first_phase = plan[0][0] if plan else "Phase 0"
    first_task = short_title(plan[0][1][0]) if plan and plan[0][1] else "Task 00"
    checklists = ""
    for title, items in plan:
        checklists += f"## {title}\n\n" + "\n".join(f"- [ ] {short_title(i)}" for i in items) + "\n\n"
    if template and template.exists():
        t = template.read_text(encoding="utf-8")
        return (t.replace("{{FIRST_PHASE}}", first_phase).replace("{{FIRST_TASK}}", first_task)
                 .replace("{{PHASE_CHECKLISTS}}", checklists.rstrip() + "\n").replace("{{PROJECT_NAME}}", prd.title()))
    return f"# Progress Tracker\n\n**Phase:** {first_phase}\n**Next:** {first_task}\n\n---\n\n{checklists}## Decisions Log\n\n## Open Questions\n\n"


def open_questions(prd: Prd) -> str:
    rows = table_rows(prd.sub("0.4"))[1:]
    rows = [r for r in rows if any(c for c in r)]
    return "\n".join(f"- {r[0]} {r[1]} (blocks {r[2] if len(r) > 2 else '?'})" for r in rows if len(r) > 1 and r[1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("prd")
    ap.add_argument("--out", default="context")
    ap.add_argument("--files", default=",".join(ALL_FILES))
    ap.add_argument("--phase0-extra", action="append", default=[])
    ap.add_argument("--skip-task", default="", help="comma list of foundation tasks to drop: adr,scaffold,ci,database,auth,tenancy,audit,contract,ui,agents,slice")
    ap.add_argument("--no-mock-first", action="store_true")
    ap.add_argument("--packs", default="", help="comma list of packs (see scripts/packs.py detect): adds their tasks, checklist gates and deferred triggers")
    ap.add_argument("--packs-dir", default="", help="folder holding the packs (default: next to the harness)")
    ap.add_argument("--tracker-template", help="progress-tracker template (defaults to templates/context/progress-tracker.md next to this script)")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    prd_path = Path(a.prd)
    if not prd_path.exists():
        print(f"not found: {prd_path}", file=sys.stderr)
        return 2
    prd = Prd(prd_path)
    wanted = [f.strip() for f in a.files.split(",") if f.strip()]
    bad = [f for f in wanted if f not in ALL_FILES]
    if bad:
        print(f"unknown --files {bad}; choose from {ALL_FILES}", file=sys.stderr)
        return 2
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    warns: list[str] = []
    rel = a.prd.replace("\\", "/")
    plan: list[tuple[str, list[str]]] = []
    outputs: dict[str, str] = {}
    build_text, plan = build_plan(prd, rel, a, warns)
    if "overview" in wanted:
        outputs["project-overview.md"] = overview(prd, rel, warns)
    if "architecture" in wanted:
        outputs["architecture.md"] = architecture(prd, rel, warns)
    if "build-plan" in wanted:
        outputs["build-plan.md"] = build_text
    if "progress-log" in wanted:
        outputs["progress-log.md"] = PROGRESS_LOG
    if "progress-tracker" in wanted:
        tpl = Path(a.tracker_template) if a.tracker_template else Path(__file__).resolve().parents[1] / "context" / "progress-tracker.md"
        text = tracker(prd, plan, tpl)
        oq = open_questions(prd)
        if oq:
            text = text.replace("_Anything the source documents leave undecided. Resolve or escalate before the task that depends on it._",
                                "_From PRD §0.4. Resolve or escalate before the task that depends on it._\n\n" + oq)
        outputs["progress-tracker.md"] = text

    for name, content in outputs.items():
        target = out / name
        if target.exists() and not a.force:
            print(f"skipped (exists): {target}   (use --force to overwrite)")
            continue
        target.write_text(content, encoding="utf-8", newline="\n")
        print(f"wrote {target}")
    for w in warns:
        print(f"warning: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
