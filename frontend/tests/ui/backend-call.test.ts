// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { callBackend } from "@/lib/auth/server";

const backend = vi.fn();
beforeEach(() => {
  vi.stubGlobal("fetch", backend);
});
afterEach(() => {
  backend.mockReset();
  vi.unstubAllGlobals();
});

const reset = () => Object.assign(new TypeError("fetch failed"), { cause: { code: "ECONNRESET", message: "read ECONNRESET" } });

describe("callBackend (the web server's call to the API)", () => {
  it("retries once when a kept-alive connection was closed while idle, and then succeeds", async () => {
    backend.mockRejectedValueOnce(reset()).mockResolvedValueOnce(new Response("{}", { status: 200 }));
    const res = await callBackend("/api/v1/auth/login", { email: "a@b.com" });
    expect(res.status).toBe(200);
    expect(backend).toHaveBeenCalledTimes(2);
  });

  it("gives up after that one retry", async () => {
    backend.mockRejectedValue(reset());
    await expect(callBackend("/api/v1/auth/login", {})).rejects.toBeDefined();
    expect(backend).toHaveBeenCalledTimes(2);
  });

  it("never retries a timeout or any other failure", async () => {
    backend.mockRejectedValue(Object.assign(new Error("The operation was aborted due to timeout"), { name: "TimeoutError" }));
    await expect(callBackend("/api/v1/auth/login", {})).rejects.toBeDefined();
    expect(backend).toHaveBeenCalledTimes(1);
  });

  it("forwards extra headers, skipping empty ones", async () => {
    backend.mockResolvedValue(new Response("{}", { status: 200 }));
    await callBackend("/api/v1/auth/register", {}, { "x-forwarded-for": "203.0.113.9", "x-empty": "" });
    const init = backend.mock.calls[0][1];
    expect(init.headers["x-forwarded-for"]).toBe("203.0.113.9");
    expect("x-empty" in init.headers).toBe(false);
  });
});
