#!/usr/bin/env python3
"""
Render a context template: keep or drop marked blocks, strip the markers, substitute {{VARS}}.

  render.py IN OUT [--stack dotnet,typescript] [--when tenancy,ui,money] [--optional touch,dashboards]
                   [--var KEY=VALUE ...] [--ecosystem dotnet,node]

Markers (each closed by `<!-- @end -->`, or for dependabot by the next `# @ecosystem:` line):
  <!-- @stack:X -->      kept only if X is in --stack
  <!-- @when:X -->       kept only if X is in --when ("always" is always kept)
  <!-- @optional:X -->   kept only if X is in --optional
  # @ecosystem:X        (dependabot.yml.tmpl) kept only if X is in --ecosystem or is "always"
An HTML comment that starts with "Template notes" is removed entirely.

Prints any {{PLACEHOLDER}} still present so the caller can fill it in. Exit code 0 always,
unless the input has an unclosed block (exit 2).
"""
import argparse
import re
import sys
from pathlib import Path

OPEN = re.compile(r"^\s*<!-- @(stack|when|optional):([\w-]+) -->\s*$")
CLOSE = re.compile(r"^\s*<!-- @end -->\s*$")
ECO = re.compile(r"^\s*# @ecosystem:([\w-]+)\s*$")


def csv(value: str) -> set[str]:
    return {v.strip() for v in value.split(",") if v.strip()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--stack", default="")
    ap.add_argument("--when", default="")
    ap.add_argument("--optional", default="")
    ap.add_argument("--ecosystem", default="")
    ap.add_argument("--var", action="append", default=[])
    a = ap.parse_args()

    keep = {"stack": csv(a.stack), "when": csv(a.when) | {"always"}, "optional": csv(a.optional)}
    eco = csv(a.ecosystem) | {"always"}
    text = Path(a.src).read_text(encoding="utf-8")
    text = re.sub(r"<!-- Template notes.*?-->\n?", "", text, flags=re.S)

    out: list[str] = []
    stack: list[bool] = []  # per open block: is it kept
    eco_keep = True
    is_eco_file = any(ECO.match(l) for l in text.splitlines())
    for line in text.splitlines():
        m = OPEN.match(line)
        if m:
            stack.append(m.group(2) in keep[m.group(1)])
            continue
        if CLOSE.match(line):
            if not stack:
                print("unmatched @end", file=sys.stderr)
                return 2
            stack.pop()
            continue
        e = ECO.match(line)
        if e:
            eco_keep = e.group(1) in eco
            continue
        if all(stack) and (eco_keep or not is_eco_file):
            out.append(line)
    if stack:
        print("unclosed block in template", file=sys.stderr)
        return 2

    result = "\n".join(out) + "\n"
    result = re.sub(r"\n{3,}", "\n\n", result)
    for pair in a.var:
        k, _, v = pair.partition("=")
        result = result.replace("{{" + k + "}}", v)
    Path(a.dst).parent.mkdir(parents=True, exist_ok=True)
    Path(a.dst).write_text(result, encoding="utf-8", newline="\n")
    left = sorted(set(re.findall(r"\{\{[A-Za-z_]+\}\}", result)))
    print(f"wrote {a.dst}" + (f"; unfilled: {' '.join(left)}" if left else "; no placeholders left"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
