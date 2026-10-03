// Dependency-audit gate. `npm audit` fails on advisories that have no upstream fix, so a plain gate is either
// permanently red or switched off. This one fails on any high/critical advisory that is NOT in
// audit-allowlist.json, and on any allow-list entry that has expired or no longer matches anything.
//   node scripts/check-audit.mjs            (runs `npm audit --json`)
//   node scripts/check-audit.mjs file.json  (checks a saved report; used by the tests)
import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const BLOCKING = new Set(["high", "critical"]);

export function advisories(report) {
  const found = new Map();
  for (const vuln of Object.values(report.vulnerabilities ?? {})) {
    for (const via of vuln.via ?? []) {
      if (typeof via === "object") {
        // an advisory without a url cannot be allow-listed, so it is keyed by title and always blocks if serious
        const id = via.url ? via.url.split("/").pop() : `no-url:${via.name}:${via.title}`;
        found.set(id, { severity: via.severity, name: via.name, title: via.title });
      }
    }
  }
  return found;
}

export function evaluate(report, allowlist, today = new Date()) {
  const problems = [];
  if (report.error || typeof report.vulnerabilities !== "object") {
    // npm could not produce an audit (registry or network failure): that is not a clean bill of health
    return [`npm audit did not produce a report: ${JSON.stringify(report.error ?? "no vulnerabilities field").slice(0, 200)}`];
  }
  const found = advisories(report);
  const allowed = new Map(allowlist.map((entry) => [entry.id, entry]));
  for (const [id, info] of found) {
    if (!BLOCKING.has(info.severity)) continue;
    const entry = allowed.get(id);
    if (!entry) problems.push(`${info.severity} advisory ${id} in ${info.name} is not allow-listed: ${info.title}`);
    else if (!(new Date(entry.expires) >= today)) problems.push(`allow-list entry ${id} expired or has an invalid date (${entry.expires}): re-review it`);
  }
  for (const entry of allowlist) {
    if (!entry.reason || !entry.expires) problems.push(`allow-list entry ${entry.id} needs a reason and an expiry date`);
    if (!found.has(entry.id)) problems.push(`allow-list entry ${entry.id} matches nothing any more: remove it`);
  }
  return problems;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const allowlist = JSON.parse(readFileSync(new URL("../audit-allowlist.json", import.meta.url), "utf8")).allow;
  let raw;
  if (process.argv[2]) raw = readFileSync(process.argv[2], "utf8");
  else {
    try {
      raw = execSync("npm audit --json", { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
    } catch (error) {
      raw = error.stdout; // npm audit exits non-zero when it finds anything
    }
  }
  const problems = evaluate(JSON.parse(raw), allowlist);
  if (problems.length) {
    console.error("dependency audit gate FAILED:\n- " + problems.join("\n- "));
    process.exit(1);
  }
  console.log(`dependency audit gate passed (${allowlist.length} reviewed advisories allow-listed)`);
}
