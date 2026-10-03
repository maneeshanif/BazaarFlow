import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useSubmit } from "@/hooks/useSubmit";
import { ApiError } from "@/lib/api/client";

describe("useSubmit: one request at a time (task 52)", () => {
  it("ignores a second call while the first is still running, so a double click creates one record", async () => {
    let release: (v: string) => void = () => undefined;
    const action = vi.fn(() => new Promise<string>((resolve) => (release = resolve)));
    const { result } = renderHook(() => useSubmit(action));

    let first: Promise<string | undefined> = Promise.resolve(undefined);
    let second: Promise<string | undefined> = Promise.resolve(undefined);
    await act(async () => {
      first = result.current.run();
      second = result.current.run();
    });
    expect(result.current.pending).toBe(true);
    await act(async () => {
      release("created");
      await Promise.all([first, second]);
    });
    expect(action).toHaveBeenCalledTimes(1);
    expect(await first).toBe("created");
    expect(await second).toBeUndefined();
    expect(result.current.pending).toBe(false);
  });

  it("keeps the server's per-field messages so the form can show them inline", async () => {
    const failure = new ApiError(422, "price: bad", "validation_failed", { price: "Enter an amount" });
    const { result } = renderHook(() => useSubmit(async () => Promise.reject(failure)));
    await act(async () => {
      await result.current.run();
    });
    expect(result.current.fieldErrors).toEqual({ price: "Enter an amount" });
    expect(result.current.error?.status).toBe(422);
  });

  it("allows another attempt after a failure", async () => {
    const action = vi.fn<() => Promise<string>>().mockRejectedValueOnce(new ApiError(500, "boom")).mockResolvedValueOnce("ok");
    const { result } = renderHook(() => useSubmit(action));
    await act(async () => void (await result.current.run()));
    let out: string | undefined;
    await act(async () => void (out = await result.current.run()));
    expect(out).toBe("ok");
    expect(result.current.error).toBeNull();
  });
});
