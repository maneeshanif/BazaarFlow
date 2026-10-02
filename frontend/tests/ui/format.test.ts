import { describe, expect, it } from "vitest";
import { formatDate, formatDateTime, formatMoney, formatNumber } from "@/lib/format";

describe("lib/format (PRD §16: one formatting module)", () => {
  it("formats PKR money with grouping and no decimals for whole amounts", () => {
    expect(formatMoney(12500)).toBe("Rs 12,500");
    expect(formatMoney("42500")).toBe("Rs 42,500");
  });
  it("keeps two decimals when there are cents", () => {
    expect(formatMoney(1299.5)).toBe("Rs 1,299.50");
  });
  it("shows negatives with a sign, or in parentheses for financial reports", () => {
    expect(formatMoney(-500)).toBe("-Rs 500");
    expect(formatMoney(-500, { negative: "parentheses" })).toBe("(Rs 500)");
  });
  it("is exact for decimal strings and never shows floating point noise", () => {
    expect(formatMoney("0.30")).toBe("Rs 0.30");
    expect(formatMoney(0.1 + 0.2)).toBe("Rs 0.30");
  });
  it("renders a dash for missing values", () => {
    expect(formatMoney(null)).toBe("-");
    expect(formatMoney(undefined)).toBe("-");
  });
  it("formats numbers with a precision", () => {
    expect(formatNumber(1234567)).toBe("1,234,567");
    expect(formatNumber(3.14159, { precision: 2 })).toBe("3.14");
  });
  it("renders UTC timestamps in the shop's timezone (Asia/Karachi, UTC+5)", () => {
    expect(formatDateTime("2026-10-01T20:30:00Z")).toBe("02 Oct 2026, 01:30");
    expect(formatDate("2026-10-01T20:30:00Z")).toBe("02 Oct 2026");
  });
  it("honours a different timezone", () => {
    expect(formatDateTime("2026-10-01T20:30:00Z", { timezone: "UTC" })).toBe("01 Oct 2026, 20:30");
  });
});
