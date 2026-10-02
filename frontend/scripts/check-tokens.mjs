/**
 * Design-token checker (task 07): colour, type and spacing may come only from tokens.
 *
 * Flags, in app/ and components/ source files:
 *   - hex / rgb() / hsl() colour literals (hsl(var(--x)) is fine: it is a token)
 *   - raw Tailwind palette classes (bg-red-500, text-slate-700) and white/black classes
 *   - arbitrary colour / padding / margin / gap / font-size values (p-[13px], text-[15px], bg-[#123])
 *
 * New files must have zero violations. Legacy files are listed with their violation count in
 * token-baseline.json and may only go down (a ratchet). `--write-baseline` regenerates it.
 * components/ui/ (shadcn primitives) is excluded: they already consume the shadcn token variables.
 */
import { readdirSync, readFileSync, statSync, writeFileSync, existsSync } from "node:fs";
import { join, relative, sep } from "node:path";

// Run from the frontend folder (npm run check:tokens); vitest does not give file: URLs, so no import.meta.url here.
const ROOT = process.cwd();
const SCAN_DIRS = ["app", "components"];
const SKIP = [`components${sep}ui${sep}`, `${sep}node_modules${sep}`, `${sep}.next${sep}`];
const EXT = /\.(tsx?|jsx?|mjs)$/;
const BASELINE = join(ROOT, "token-baseline.json");

const PALETTE =
  "slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose";
const PREFIX = "bg|text|border|ring|fill|stroke|from|via|to|outline|divide|shadow|decoration|accent|caret|placeholder";

const RULES = [
  { name: "hex colour", re: /(?<!href=["'])(?<![\w&])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b(?![\w-])/g },
  { name: "rgb/hsl literal", re: /\b(?:rgba?|hsla?)\(\s*\d/g },
  { name: "palette class", re: new RegExp(`\\b(?:${PREFIX})-(?:${PALETTE})-\\d{2,3}\\b`, "g") },
  { name: "white/black class", re: new RegExp(`\\b(?:${PREFIX})-(?:white|black)\\b`, "g") },
  { name: "arbitrary spacing/type", re: /\b(?:p|px|py|pt|pb|pl|pr|m|mx|my|mt|mb|ml|mr|gap|space-x|space-y|text)-\[[0-9.]+(?:px|rem|em)\]/g },
];

/** Returns [{rule, text, line}] for one source string. */
export function scanSource(source, _file = "") {
  const found = [];
  const lines = source.split("\n");
  lines.forEach((line, i) => {
    const seen = new Set();
    for (const { name, re } of RULES) {
      re.lastIndex = 0;
      for (const m of line.matchAll(re)) {
        // an arbitrary colour in brackets, e.g. bg-[#123456], is reported once as a hex colour
        const key = `${m.index}:${m[0]}`;
        if (seen.has(key)) continue;
        seen.add(key);
        found.push({ rule: name, text: m[0], line: i + 1 });
      }
    }
  });
  return found;
}

/**
 * found / baseline: { file: count }. Failures: any count above the baseline (0 for files not in it).
 * Improved: baseline entries whose count went down.
 */
export function evaluate(found, baseline) {
  const failures = [];
  const improved = [];
  for (const [file, now] of Object.entries(found)) {
    const allowed = baseline[file] ?? 0;
    if (now > allowed) failures.push({ file, allowed, now });
  }
  for (const [file, was] of Object.entries(baseline)) {
    const now = found[file] ?? 0;
    if (now < was) improved.push({ file, was, now });
  }
  return { failures, improved };
}

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (SKIP.some((s) => full.includes(s))) continue;
    const st = statSync(full);
    if (st.isDirectory()) walk(full, out);
    else if (EXT.test(name)) out.push(full);
  }
  return out;
}

function countAll() {
  const counts = {};
  const details = {};
  for (const d of SCAN_DIRS) {
    const dir = join(ROOT, d);
    if (!existsSync(dir)) continue;
    for (const file of walk(dir)) {
      const rel = relative(ROOT, file).split(sep).join("/");
      const hits = scanSource(readFileSync(file, "utf8"), rel);
      if (hits.length) {
        counts[rel] = hits.length;
        details[rel] = hits;
      }
    }
  }
  return { counts, details };
}

function main() {
  const { counts, details } = countAll();
  if (process.argv.includes("--write-baseline")) {
    const sorted = Object.fromEntries(Object.entries(counts).sort(([a], [b]) => a.localeCompare(b)));
    writeFileSync(BASELINE, JSON.stringify(sorted, null, 2) + "\n");
    console.log(`baseline written: ${Object.keys(sorted).length} legacy files, ${Object.values(sorted).reduce((a, b) => a + b, 0)} violations`);
    return 0;
  }
  const baseline = existsSync(BASELINE) ? JSON.parse(readFileSync(BASELINE, "utf8")) : {};
  const { failures, improved } = evaluate(counts, baseline);
  if (failures.length) {
    console.error("TOKEN CHECK FAILED: colour, type and spacing must come from tokens (context/ui-tokens.md)");
    for (const f of failures) {
      console.error(`  ${f.file}: ${f.now} violation(s), allowed ${f.allowed}`);
      for (const h of details[f.file].slice(0, 5)) console.error(`    line ${h.line}: ${h.rule}  ${h.text}`);
    }
    return 1;
  }
  if (improved.length) {
    console.log("note: these legacy files improved; run `npm run check:tokens -- --write-baseline` to lock it in:");
    for (const i of improved) console.log(`  ${i.file}: ${i.was} -> ${i.now}`);
  }
  const legacy = Object.keys(baseline).length;
  console.log(`token check passed (${legacy} legacy files still on the baseline)`);
  return 0;
}

if (process.argv[1] && /check-tokens\.mjs$/.test(process.argv[1])) process.exit(main());
