// @vitest-environment node
import { describe, expect, it } from "vitest";
import { advisories, evaluate } from "../../scripts/check-audit.mjs";

const report = (...items: { id: string; severity: string; name?: string }[]) => ({
  vulnerabilities: Object.fromEntries(
    items.map((item, i) => [
      `pkg${i}`,
      { via: [{ url: `https://github.com/advisories/${item.id}`, severity: item.severity, name: item.name ?? `pkg${i}`, title: "t" }, "other"] },
    ]),
  ),
});
const allow = (id: string, extra = {}) => ({ id, reason: "reviewed", expires: "2999-01-01", ...extra });

describe("dependency audit gate", () => {
  it("passes when nothing blocking is found", () => {
    expect(evaluate(report({ id: "GHSA-aaaa", severity: "moderate" }), [])).toEqual([]);
    expect(evaluate({ vulnerabilities: {} }, [])).toEqual([]);
  });
  it("fails on a new high or critical advisory", () => {
    for (const severity of ["high", "critical"]) {
      const problems = evaluate(report({ id: "GHSA-new", severity }), []);
      expect(problems).toHaveLength(1);
      expect(problems[0]).toContain("GHSA-new");
    }
  });
  it("accepts a reviewed advisory", () => {
    expect(evaluate(report({ id: "GHSA-ok", severity: "high" }), [allow("GHSA-ok")])).toEqual([]);
  });
  it("fails when the review has expired, so nothing stays accepted forever", () => {
    const problems = evaluate(report({ id: "GHSA-ok", severity: "high" }), [allow("GHSA-ok", { expires: "2020-01-01" })]);
    expect(problems.join()).toContain("expired");
  });
  it("fails on an allow-list entry that matches nothing, or has no reason or expiry", () => {
    expect(evaluate(report(), [allow("GHSA-gone")]).join()).toContain("matches nothing");
    expect(evaluate(report({ id: "GHSA-x", severity: "high" }), [{ id: "GHSA-x" }]).join()).toContain("needs a reason");
  });
  it("fails closed when npm could not produce a report (registry or network failure)", () => {
    expect(evaluate({ error: { code: "ENOTFOUND", summary: "network" } }, []).join()).toContain("did not produce a report");
    expect(evaluate({}, [allow("GHSA-ok")]).join()).toContain("did not produce a report");
  });
  it("treats an invalid expiry date as expired instead of never expiring", () => {
    const problems = evaluate(report({ id: "GHSA-ok", severity: "high" }), [allow("GHSA-ok", { expires: "2027-1-15x" })]);
    expect(problems.join()).toContain("invalid date");
  });
  it("still blocks a serious advisory that has no url", () => {
    const noUrl = { vulnerabilities: { p: { via: [{ severity: "high", name: "p", title: "t" }] } } };
    expect(evaluate(noUrl, [])).toHaveLength(1);
  });
  it("reads advisory ids from the npm report shape", () => {
    expect([...advisories(report({ id: "GHSA-1", severity: "high" })).keys()]).toEqual(["GHSA-1"]);
  });
});
