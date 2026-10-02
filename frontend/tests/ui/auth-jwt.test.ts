import { describe, expect, it } from "vitest";
import { decodeExp, msUntilRefresh, safeNextPath } from "@/lib/auth/jwt";

const token = (payload: object) => `h.${Buffer.from(JSON.stringify(payload)).toString("base64url")}.s`;

describe("jwt helpers (the token is only read for its expiry; the server is the authority)", () => {
  it("reads exp in seconds", () => {
    expect(decodeExp(token({ exp: 1_800_000_000 }))).toBe(1_800_000_000);
  });
  it("returns null for anything that is not a token with an exp", () => {
    expect(decodeExp("garbage")).toBeNull();
    expect(decodeExp(token({ sub: "x" }))).toBeNull();
    expect(decodeExp("a.%%%.c")).toBeNull();
  });
  it("schedules the refresh a minute before expiry", () => {
    const now = 1_000_000_000_000;
    expect(msUntilRefresh(token({ exp: now / 1000 + 600 }), now)).toBe(540_000);
  });
  it("never schedules in a tight loop: at least 5 s even for a token that is nearly expired", () => {
    const now = 1_000_000_000_000;
    expect(msUntilRefresh(token({ exp: now / 1000 + 30 }), now)).toBe(5_000);
    expect(msUntilRefresh(token({ exp: now / 1000 - 10 }), now)).toBe(5_000);
  });
  it("retries in 30 s when the expiry cannot be read", () => {
    expect(msUntilRefresh("garbage", 1_000_000_000_000)).toBe(30_000);
  });
});

describe("safeNextPath: where to go after sign-in", () => {
  it("accepts same-site paths", () => {
    expect(safeNextPath("/dashboard/orders?x=1")).toBe("/dashboard/orders?x=1");
  });
  it.each(["https://evil.example", "//evil.example", "/\\evil.example", "javascript:alert(1)", "/\t/evil.example", "/\n/evil.example", "/\r/evil.example", "/ /evil.example", "dashboard", "", null, undefined])(
    "rejects %s",
    (value) => {
      expect(safeNextPath(value as string | null | undefined)).toBeNull();
    },
  );
});
