import { expect, test } from "@playwright/test";
import { visit } from "./support";

/**
 * Task 54 acceptance: ONE browser test that follows the critical flow of a new shopkeeper end to end, against the real
 * backend: create a shop, add a product, sell it, see the order, the stock and the home figures change.
 * Needs the stack from `uv run python scripts/e2e_auth_stack.py`.
 */
test.skip(!process.env.E2E_AUTH, "run through scripts/e2e_auth_stack.py");

test("a new shopkeeper creates a shop, adds a product and makes a sale", async ({ page }) => {
  test.setTimeout(120_000);
  const stamp = Date.now();

  // 1. create the shop
  await page.goto("/register");
  await page.getByLabel(/^Your name/).fill("Critical Flow");
  await page.getByLabel(/^Shop name/).fill(`Flow Shop ${stamp}`);
  await page.getByLabel(/^Email/).fill(`flow-${stamp}@example.com`);
  await page.getByLabel(/^Password/).fill("unusual-passphrase-42");
  await page.getByLabel(/^Phone/).fill("0300 1234567");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Create shop" }).click();
  await expect(page).toHaveURL(/\/inventory$/); // a new shop starts at its first step

  // 2. add a product
  await visit(page, "/inventory/new");
  await page.getByLabel(/^SKU/).fill(`FLOW-${stamp}`);
  await page.getByLabel(/^Name/).fill("Flow Kurta");
  await page.getByLabel(/^Price/).fill("1500");
  await page.getByLabel(/^Cost/).fill("1000");
  await page.getByLabel(/^Opening stock/).fill("5");
  await page.getByRole("button", { name: "Add product" }).click();
  await expect(page).toHaveURL(/\/inventory$/);
  await expect(page.getByRole("link", { name: "Flow Kurta" })).toBeVisible();

  // 3. sell two of it for cash
  await visit(page, "/sales/new");
  await page.getByRole("button", { name: "Add product" }).click();
  await page.getByRole("searchbox", { name: /Add a product/ }).fill("Flow Kurta");
  await page.getByRole("button", { name: /Flow Kurta/ }).click();
  await page.getByLabel("Quantity of Flow Kurta").fill("2");
  await expect(page.getByLabel("Sale totals").getByText("Rs 3,000").first()).toBeVisible();
  await page.getByRole("button", { name: "Post sale" }).click();
  await expect(page).toHaveURL(/\/orders\/[0-9a-f-]{36}$/);
  await expect(page.getByText("Rs 3,000").first()).toBeVisible();

  // 4. the stock came down, and the home screen counts the sale
  await visit(page, "/inventory");
  await expect(page.getByRole("row", { name: /Flow Kurta/ })).toContainText("3");
  await visit(page, "/dashboard");
  const figures = page.getByRole("region", { name: "Key figures" });
  await expect(figures.getByRole("link", { name: /Today sales/ })).toContainText("Rs 3,000");
  await expect(figures.getByRole("link", { name: /Today profit/ })).toContainText("Rs 1,000");
  await expect(figures.getByRole("link", { name: /Today orders/ })).toContainText("1");
});
