import { expect, test, type Page } from "@playwright/test";

/**
 * Task 53 acceptance: the performance budget lane. Measured in a real browser against the production build:
 * JavaScript sent to the browser, largest contentful paint and layout shift. The budgets are deliberately generous
 * for a local run (no network); they exist to catch a regression such as an accidental heavy library, not to tune.
 * Needs the stack from `uv run python scripts/e2e_auth_stack.py`.
 */
test.skip(!process.env.E2E_AUTH, "run through scripts/e2e_auth_stack.py");

// Baseline on 2026-10-04 (production build, compressed): landing 377 KB, signed-in home 582 KB. Budgets sit just above
// it so the lane catches a regression; lower them when the shared bundle is trimmed.
const BUDGET = { jsKb: 450, appJsKb: 650, lcpMs: 2500, cls: 0.1 };

async function measure(page: Page) {
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(500);
  return page.evaluate(async () => {
    const js = performance
      .getEntriesByType("resource")
      .filter((r) => (r as PerformanceResourceTiming).initiatorType === "script" || r.name.endsWith(".js"))
      .reduce((sum, r) => sum + ((r as PerformanceResourceTiming).encodedBodySize || 0), 0);
    const lcp = await new Promise<number>((resolve) => {
      let value = 0;
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) value = entry.startTime;
      }).observe({ type: "largest-contentful-paint", buffered: true });
      setTimeout(() => resolve(value), 300);
    });
    const cls = await new Promise<number>((resolve) => {
      let value = 0;
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries() as unknown as { value: number; hadRecentInput: boolean }[]) if (!entry.hadRecentInput) value += entry.value;
      }).observe({ type: "layout-shift", buffered: true });
      setTimeout(() => resolve(value), 300);
    });
    return { jsKb: Math.round(js / 1024), lcpMs: Math.round(lcp), cls: Math.round(cls * 1000) / 1000 };
  });
}

test("the landing page stays inside the performance budget", async ({ page }) => {
  await page.goto("/");
  const m = await measure(page);
  console.log("PERF landing", JSON.stringify(m));
  expect(m.jsKb, "JavaScript sent to the browser (KB, compressed)").toBeLessThanOrEqual(BUDGET.jsKb);
  expect(m.lcpMs, "largest contentful paint (ms)").toBeLessThanOrEqual(BUDGET.lcpMs);
  expect(m.cls, "cumulative layout shift").toBeLessThanOrEqual(BUDGET.cls);
});

test("the signed-in home screen stays inside the performance budget", async ({ page }) => {
  await page.goto("/sign-in?next=/dashboard");
  await page.getByLabel("Email").fill(process.env.E2E_OWNER_EMAIL ?? "owner@example.com");
  await page.getByLabel("Password").fill(process.env.E2E_PASSWORD ?? "e2e-password-1");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("region", { name: "Key figures" })).toBeVisible();
  const m = await measure(page);
  console.log("PERF dashboard", JSON.stringify(m));
  expect(m.jsKb, "JavaScript sent to the browser (KB, compressed)").toBeLessThanOrEqual(BUDGET.appJsKb);
  expect(m.cls).toBeLessThanOrEqual(BUDGET.cls);
});
