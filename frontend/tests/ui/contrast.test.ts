import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

/**
 * WCAG AA contrast (4.5:1 for text) for the token pairs the components actually use, in both themes.
 * The values are read from app/global.css, so changing a token cannot silently break accessibility.
 */
const CR = String.fromCharCode(13);
const css = readFileSync("app/global.css", "utf8").split(CR).join("");

function block(selector: string): Record<string, string> {
  const start = css.indexOf(`${selector} {\n  --color-canvas`);
  const body = css.slice(start, css.indexOf("\n}\n", start));
  return Object.fromEntries([...body.matchAll(/--color-([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})/g)].map((m) => [m[1], m[2]]));
}

const channel = (v: number) => {
  const s = v / 255;
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
};
const luminance = (hex: string) => {
  const n = parseInt(hex.slice(1), 16);
  return 0.2126 * channel((n >> 16) & 255) + 0.7152 * channel((n >> 8) & 255) + 0.0722 * channel(n & 255);
};
const ratio = (a: string, b: string) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

const themes = { light: block(":root"), dark: block(".dark") };

// [foreground token, background token]
const PAIRS: [string, string][] = [
  ["fg", "surface"],
  ["fg", "canvas"],
  ["fg-muted", "surface"],
  ["fg-muted", "canvas"],
  ["fg-subtle", "surface"], // placeholders, hints, "Soon" labels
  ["fg-inverse", "action"],
  ["fg-inverse", "danger"],
  ["action", "action-subtle"],
  ["success", "success-subtle"],
  ["warning", "warning-subtle"],
  ["danger", "danger-subtle"],
  ["info", "info-subtle"],
  ["neutral", "neutral-subtle"],
  ["action", "surface"],
  ["positive", "surface"],
  ["negative", "surface"],
];

describe.each(Object.entries(themes))("%s theme: text contrast >= 4.5:1", (_name, tokens) => {
  it("defines every token the pairs need", () => {
    for (const [fg, bg] of PAIRS) {
      expect(tokens[fg], fg).toBeDefined();
      expect(tokens[bg], bg).toBeDefined();
    }
  });
  it.each(PAIRS)("%s on %s", (fg, bg) => {
    expect(ratio(tokens[fg], tokens[bg])).toBeGreaterThanOrEqual(4.5);
  });
});
