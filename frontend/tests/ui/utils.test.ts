import { describe, expect, it } from "vitest";
import { cn } from "@/lib/utils";

describe("cn", () => {
  it("keeps a text colour next to one of our font sizes (regression: primary buttons lost their white text)", () => {
    expect(cn("bg-action text-fg-inverse", "h-control-md px-3 text-ui-base")).toBe("bg-action text-fg-inverse h-control-md px-3 text-ui-base");
    expect(cn("text-ui-sm text-fg", "text-ui-lg")).toBe("text-fg text-ui-lg"); // a later size still replaces an earlier one
    expect(cn("text-fg-muted", "text-fg")).toBe("text-fg"); // and a later colour replaces an earlier colour
  });
});
