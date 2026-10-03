import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { productSchema, stockMovementSchema } from "@/lib/validation/product";

type Shared = { base: Record<string, unknown>; cases: { field: string; value: unknown }[] };
const shared = JSON.parse(readFileSync(resolve(__dirname, "../../../contracts/invalid-product-inputs.json"), "utf-8")) as Shared;

describe("product validation mirrors the API (task 52)", () => {
  it("accepts the base input the API accepts", () => {
    expect(productSchema.safeParse(shared.base).success).toBe(true);
  });

  it.each(shared.cases.map((c) => [c.field, c.value] as const))("rejects %s = %j, as the API does", (field, value) => {
    const result = productSchema.safeParse({ ...shared.base, [field]: value });
    expect(result.success).toBe(false);
    if (!result.success) expect(result.error.issues.map((i) => i.path[0])).toContain(field);
  });

  it("explains the problem in words a shopkeeper can act on", () => {
    const result = productSchema.safeParse({ ...shared.base, price: "abc" });
    expect(result.success ? "" : result.error.issues[0]?.message).toMatch(/amount like 2500/);
  });

  it("stock movements: a zero change is refused", () => {
    expect(stockMovementSchema.safeParse({ delta: "0", reason: "purchase" }).success).toBe(false);
    expect(stockMovementSchema.safeParse({ delta: "-3", reason: "adjustment" }).success).toBe(true);
    expect(stockMovementSchema.safeParse({ delta: "2", reason: "sale" }).success).toBe(false);
  });
});
