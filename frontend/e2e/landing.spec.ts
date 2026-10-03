import { expect, test } from "@playwright/test";

/**
 * Tasks 46 and 47 acceptance, against the REAL backend: the public landing page explains the product, and one click
 * opens a private demo shop that is already full of data and where the chat works. Needs the stack from
 * `uv run python scripts/e2e_auth_stack.py`.
 */
test.skip(!process.env.E2E_AUTH, "run through scripts/e2e_auth_stack.py");

test("the landing page explains the product and offers the demo and sign-up", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Tell it what you sold");
  await expect(page.getByText(/Example: the shopkeeper writes/)).toBeAttached();
  await expect(page.getByRole("heading", { name: "You stay in charge of your shop." })).toBeVisible();
  await expect(page.getByRole("link", { name: "Create your shop" }).first()).toHaveAttribute("href", "/register");
  // no horizontal scroll on a phone
  await page.setViewportSize({ width: 360, height: 800 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("one click opens a private demo shop with data, and the chat works in it", async ({ page }) => {
  test.setTimeout(150_000);
  await page.goto("/");
  await page.getByRole("button", { name: "Try the live demo" }).first().dblclick();
  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 90_000 }); // the shop is seeded on the way in
  const figures = page.getByRole("region", { name: "Key figures" });
  await expect(figures.getByRole("link", { name: /Low-stock items/ })).toBeVisible();
  await page.getByLabel("Period", { exact: true }).selectOption("7d");
  await expect(figures.getByRole("link", { name: /Last 7 days orders/ })).toContainText("5");

  await page.goto("/sales/chat");
  await page.getByLabel("Your message").fill("sell 1 cotton shirt to ali");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText(/Draft sale for Ali Raza/)).toBeVisible();
});
