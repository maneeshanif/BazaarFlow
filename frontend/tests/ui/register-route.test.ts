// @vitest-environment node
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { POST as register } from "@/app/api/auth/register/route";

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
const post = (body: unknown, headers: Record<string, string> = {}) =>
  new NextRequest("http://localhost:3000/api/auth/register", {
    method: "POST",
    headers: { "content-type": "application/json", ...headers },
    body: JSON.stringify(body),
  });

const form = {
  full_name: "Ali Raza",
  email: "ali@example.com",
  password: "unusual-passphrase-42",
  shop_name: "Ali Mart",
  phone: "+923001234567",
  accept_terms: true,
};
const tokens = { access_token: "access.jwt.value", refresh_token: "r".repeat(48), tenant_id: "t1", role: "owner" };

describe("POST /api/auth/register (BFF)", () => {
  it("keeps the refresh token in an httpOnly cookie and returns only the access token", async () => {
    backend.mockResolvedValue(json(tokens, 201));
    const res = await register(post(form));
    expect(res.status).toBe(201);
    const body = await res.json();
    expect(body).toEqual({ access_token: "access.jwt.value", tenant_id: "t1", role: "owner" });
    expect(JSON.stringify(body)).not.toContain(tokens.refresh_token);
    const cookie = res.headers.get("set-cookie") ?? "";
    expect(cookie).toContain(`bf_refresh=${tokens.refresh_token}`);
    expect(cookie.toLowerCase()).toContain("httponly");
  });

  it("forwards only the known fields and the visitor's address, never an injected one", async () => {
    backend.mockResolvedValue(json(tokens, 201));
    await register(post({ ...form, role: "owner", tenant_id: "evil", is_platform_admin: true }, { "x-forwarded-for": "203.0.113.9" }));
    const [url, init] = backend.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/auth\/register$/);
    expect(JSON.parse(init.body)).toEqual(form);
    expect(init.headers["x-forwarded-for"]).toBe("203.0.113.9");
  });

  it("passes the API's refusals through without setting a cookie", async () => {
    const refusal = { detail: "password: is too common", code: "validation_failed", errors: [{ field: "password", message: "is too common" }] };
    backend.mockResolvedValue(json(refusal, 422));
    const res = await register(post(form));
    expect(res.status).toBe(422);
    expect(res.headers.get("set-cookie")).toBeNull();
    expect((await res.json()).errors[0].field).toBe("password");
    backend.mockResolvedValue(json({ detail: "Email already registered" }, 409));
    expect((await register(post(form))).status).toBe(409);
    backend.mockResolvedValue(json({ code: "signup_rate_limited", detail: "Too many sign-ups" }, 429));
    expect((await register(post(form))).status).toBe(429);
  });

  it("rejects a body that is not an object, and a 200 without tokens sets no cookie", async () => {
    for (const body of [null, [], "x"]) expect((await register(post(body))).status).toBe(400);
    backend.mockResolvedValue(json({}, 201));
    const res = await register(post(form));
    expect(res.status).toBe(502);
    expect(res.headers.get("set-cookie")).toBeNull();
  });
});
