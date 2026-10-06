import { describe, expect, it } from "vitest";
import { billSchema, vendorPaymentSchema, vendorSchema } from "@/lib/validation/vendor";

describe("vendorSchema (PRD F-012)", () => {
  it("accepts a name with an optional phone", () => {
    expect(vendorSchema.safeParse({ name: "Karachi Cloth House", phone: "0300 1234567" }).success).toBe(true);
    expect(vendorSchema.safeParse({ name: "Karachi Cloth House", phone: "" }).success).toBe(true);
    expect(vendorSchema.safeParse({ name: "Karachi Cloth House", phone: "+92" }).success).toBe(true);
  });
  it("rejects a short or long name and a bad phone", () => {
    expect(vendorSchema.safeParse({ name: "a", phone: "" }).success).toBe(false);
    expect(vendorSchema.safeParse({ name: "n".repeat(121), phone: "" }).success).toBe(false);
    expect(vendorSchema.safeParse({ name: "Good name", phone: "abc" }).success).toBe(false);
  });
});

describe("billSchema and vendorPaymentSchema", () => {
  const bill = { amount: "1000", due_date: "", reference: "", note: "" };
  it("needs a positive amount with at most two decimals", () => {
    expect(billSchema.safeParse(bill).success).toBe(true);
    expect(billSchema.safeParse({ ...bill, amount: "0" }).success).toBe(false);
    expect(billSchema.safeParse({ ...bill, amount: "1.234" }).success).toBe(false);
    expect(billSchema.safeParse({ ...bill, amount: "abc" }).success).toBe(false);
  });
  it("accepts an empty or ISO due date only", () => {
    expect(billSchema.safeParse({ ...bill, due_date: "2026-11-01" }).success).toBe(true);
    expect(billSchema.safeParse({ ...bill, due_date: "01/11/2026" }).success).toBe(false);
  });
  it("limits reference and note length", () => {
    expect(billSchema.safeParse({ ...bill, reference: "r".repeat(61) }).success).toBe(false);
    expect(billSchema.safeParse({ ...bill, note: "n".repeat(256) }).success).toBe(false);
  });
  it("a payment needs an amount and a known method", () => {
    expect(vendorPaymentSchema.safeParse({ amount: "50", method: "bank" }).success).toBe(true);
    expect(vendorPaymentSchema.safeParse({ amount: "50", method: "cheque" }).success).toBe(false);
  });
});
