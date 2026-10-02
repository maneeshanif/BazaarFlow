// @vitest-environment node
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { POST as login } from "@/app/api/auth/login/route";
import { POST as logout } from "@/app/api/auth/logout/route";
import { POST as refresh } from "@/app/api/auth/refresh/route";

const backend = vi.fn();
beforeEach(() => {
  vi.stubGlobal("fetch", backend);
});
afterEach(() => {
  backend.mockReset();
  vi.unstubAllGlobals();
});

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
const post = (path: string, body?: unknown, cookie?: string) =>
  new NextRequest(`http://localhost:3000${path}`, {
    method: "POST",
    headers: { "content-type": "application/json", ...(cookie ? { cookie } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

const tokens = { access_token: "access.jwt.value", refresh_token: "r".repeat(48), token_type: "bearer", tenant_id: "t1", role: "owner" };

describe("POST /api/auth/login (BFF: the refresh token never reaches JavaScript)", () => {
  it("keeps the refresh token in an httpOnly cookie and returns only the access token and role", async () => {
    backend.mockResolvedValue(json(tokens));
    const res = await login(post("/api/auth/login", { email: "a@b.com", password: "correct-horse" }));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toEqual({ access_token: "access.jwt.value", tenant_id: "t1", role: "owner" });
    expect(JSON.stringify(body)).not.toContain(tokens.refresh_token);
    const cookie = res.headers.get("set-cookie") ?? "";
    expect(cookie).toContain(`bf_refresh=${tokens.refresh_token}`);
    expect(cookie.toLowerCase()).toContain("httponly");
    expect(cookie.toLowerCase()).toContain("samesite=lax");
    expect(cookie).toContain("Path=/api/auth");
  });
  it("forwards the credentials to the backend login endpoint", async () => {
    backend.mockResolvedValue(json(tokens));
    await login(post("/api/auth/login", { email: "a@b.com", password: "pw-12345678", tenant_id: "t9" }));
    const [url, init] = backend.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/auth\/login$/);
    expect(JSON.parse(init.body)).toEqual({ email: "a@b.com", password: "pw-12345678", tenant_id: "t9" });
  });
  it("passes a failed login through without setting a cookie", async () => {
    backend.mockResolvedValue(json({ detail: "Invalid email or password" }, 401));
    const res = await login(post("/api/auth/login", { email: "a@b.com", password: "nope" }));
    expect(res.status).toBe(401);
    expect(res.headers.get("set-cookie")).toBeNull();
    expect((await res.json()).detail).toBe("Invalid email or password");
  });
  it("passes the tenant choice and the lockout through", async () => {
    backend.mockResolvedValue(json({ detail: { code: "tenant_required", tenants: [{ tenant_id: "a", tenant_name: "A" }] } }, 409));
    expect((await login(post("/api/auth/login", { email: "a@b.com", password: "pw-12345678" }))).status).toBe(409);
    backend.mockResolvedValue(json({ detail: "Too many failed attempts; try again later" }, 429));
    expect((await login(post("/api/auth/login", { email: "a@b.com", password: "x" }))).status).toBe(429);
  });
  it("rejects a malformed body and survives an unreachable backend", async () => {
    expect((await login(post("/api/auth/login", { nope: true }))).status).toBe(400);
    backend.mockRejectedValue(new Error("ECONNREFUSED"));
    const res = await login(post("/api/auth/login", { email: "a@b.com", password: "pw-12345678" }));
    expect(res.status).toBe(502);
    expect(JSON.stringify(await res.json())).not.toContain("ECONNREFUSED");
  });
});

describe("POST /api/auth/refresh", () => {
  it("is a 401 without the cookie and never calls the backend", async () => {
    const res = await refresh(post("/api/auth/refresh"));
    expect(res.status).toBe(401);
    expect(backend).not.toHaveBeenCalled();
  });
  it("rotates the cookie and returns a fresh access token", async () => {
    backend.mockResolvedValue(json({ ...tokens, access_token: "new.access.jwt", refresh_token: "n".repeat(48) }));
    const res = await refresh(post("/api/auth/refresh", undefined, `bf_refresh=${tokens.refresh_token}`));
    expect(res.status).toBe(200);
    expect((await res.json()).access_token).toBe("new.access.jwt");
    expect(res.headers.get("set-cookie")).toContain(`bf_refresh=${"n".repeat(48)}`);
    expect(JSON.parse(backend.mock.calls[0][1].body)).toEqual({ refresh_token: tokens.refresh_token });
  });
  it("clears the cookie when the backend rejects the token", async () => {
    backend.mockResolvedValue(json({ detail: "Invalid refresh token" }, 401));
    const res = await refresh(post("/api/auth/refresh", undefined, "bf_refresh=stale-token-value-0123456789"));
    expect(res.status).toBe(401);
    expect(res.headers.get("set-cookie")).toMatch(/bf_refresh=;|Max-Age=0|Expires=Thu, 01 Jan 1970/i);
  });
});

describe("POST /api/auth/logout", () => {
  it("revokes the token at the backend and clears the cookie", async () => {
    backend.mockResolvedValue(new Response(null, { status: 204 }));
    const res = await logout(post("/api/auth/logout", undefined, `bf_refresh=${tokens.refresh_token}`));
    expect(res.status).toBe(204);
    expect(String(backend.mock.calls[0][0])).toMatch(/\/api\/v1\/auth\/logout$/);
    expect(res.headers.get("set-cookie")).toMatch(/Max-Age=0|Expires=Thu, 01 Jan 1970/i);
  });
  it("still clears the cookie when there is nothing to revoke or the backend is down", async () => {
    const none = await logout(post("/api/auth/logout"));
    expect(none.status).toBe(204);
    backend.mockRejectedValue(new Error("down"));
    const down = await logout(post("/api/auth/logout", undefined, `bf_refresh=${tokens.refresh_token}`));
    expect(down.status).toBe(204);
    expect(down.headers.get("set-cookie")).toMatch(/Max-Age=0|Expires=Thu, 01 Jan 1970/i);
  });
});
