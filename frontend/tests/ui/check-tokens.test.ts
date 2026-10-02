import { describe, expect, it } from "vitest";
import { evaluate, scanSource } from "../../scripts/check-tokens.mjs";

describe("token checker: tokens are the only source of colour, type and spacing", () => {
  it("flags hex, rgb and hsl literals", () => {
    expect(scanSource('const c = "#2563eb";', "a.tsx")).toHaveLength(1);
    expect(scanSource("color: rgb(10, 20, 30)", "a.tsx")).toHaveLength(1);
    expect(scanSource("color: hsl(210 40% 50%)", "a.tsx")).toHaveLength(1);
  });

  it("allows colours that come from a token variable", () => {
    expect(scanSource("color: hsl(var(--primary))", "a.tsx")).toHaveLength(0);
    expect(scanSource('className="bg-surface text-fg border-border"', "a.tsx")).toHaveLength(0);
  });

  it("flags raw Tailwind palette classes and white/black", () => {
    expect(scanSource('className="bg-red-500 text-slate-700"', "a.tsx")).toHaveLength(2);
    expect(scanSource('className="text-white border-black"', "a.tsx")).toHaveLength(2);
  });

  it("flags arbitrary colour, spacing and type values", () => {
    expect(scanSource('className="bg-[#123456]"', "a.tsx").length).toBeGreaterThan(0);
    expect(scanSource('className="p-[13px] gap-[0.7rem] text-[15px]"', "a.tsx")).toHaveLength(3);
  });

  it("ignores anchors and url fragments that only look like hex", () => {
    expect(scanSource('<a href="#main">skip</a>', "a.tsx")).toHaveLength(0);
    expect(scanSource('href="#features"', "a.tsx")).toHaveLength(0);
  });

  it("requires zero violations in new files and ratchets legacy files down", () => {
    const found = { "new.tsx": 2, "legacy.tsx": 5, "legacy-ok.tsx": 3 };
    const baseline = { "legacy.tsx": 4, "legacy-ok.tsx": 3 };
    const { failures } = evaluate(found, baseline);
    expect(failures.map((f: { file: string }) => f.file).sort()).toEqual(["legacy.tsx", "new.tsx"]);
  });

  it("reports files that improved so the baseline can be tightened", () => {
    const { improved } = evaluate({ "legacy.tsx": 1 }, { "legacy.tsx": 4 });
    expect(improved).toEqual([{ file: "legacy.tsx", was: 4, now: 1 }]);
  });
});
