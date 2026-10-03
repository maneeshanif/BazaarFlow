import { expect, test, type Page } from "@playwright/test";

import { visit } from "./support";

/**
 * Tasks 41/51 acceptance, against the REAL backend and database: an owner adds a product through the form, the list
 * shows what was stored, stock changes are recorded, and staff can look but not change.
 * Needs the stack from `uv run python scripts/e2e_auth_stack.py` (it sets E2E_AUTH=1 and starts everything).
 */
test.skip(!process.env.E2E_AUTH, "run through scripts/e2e_auth_stack.py");

const PASSWORD = process.env.E2E_PASSWORD ?? "e2e-password-1";
const OWNER = process.env.E2E_OWNER_EMAIL ?? "owner@example.com";
const STAFF = process.env.E2E_STAFF_EMAIL ?? "staff@example.com";

async function signIn(page: Page, email: string) {
  await visit(page, "/sign-in?next=%2Finventory");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/inventory$/);
}

test("an owner adds a product, sees it stored, and changes its stock", async ({ page }) => {
  const sku = `E2E-${Date.now()}`;
  await signIn(page, OWNER);

  await page.getByRole("link", { name: "Add product" }).click();
  await expect(page).toHaveURL(/\/inventory\/new$/);

  // invalid input is explained inline and nothing is saved
  await page.getByRole("button", { name: "Add product" }).click();
  await expect(page.getByText("SKU is required")).toBeVisible();

  await page.getByLabel(/^SKU/).fill(sku);
  await page.getByLabel(/^Name/).fill("E2E Kurta");
  await page.getByLabel(/^Price/).fill("1850.50");
  await page.getByLabel(/^Cost/).fill("1200");
  await page.getByLabel(/^Opening stock/).fill("9");
  await page.getByLabel(/^Reorder at/).fill("3");
  await page.getByRole("button", { name: "Add product" }).click();

  // back on the list, the product is there with the stored values
  await expect(page).toHaveURL(/\/inventory$/);
  const row = page.getByRole("row", { name: new RegExp(sku) });
  await expect(row).toContainText("E2E Kurta");
  await expect(row).toContainText("Rs 1,850.50");
  await expect(row).toContainText("in stock");

  // the same SKU twice is refused with a message under the field
  await page.getByRole("link", { name: "Add product" }).click();
  await page.getByLabel(/^SKU/).fill(sku);
  await page.getByLabel(/^Name/).fill("Duplicate");
  await page.getByLabel(/^Price/).fill("10");
  await page.getByRole("button", { name: "Add product" }).click();
  await expect(page.getByText(`A product with SKU ${sku} already exists`)).toBeVisible();

  // change its stock; the history and the quantity agree
  await visit(page, "/inventory");
  await page.getByRole("link", { name: "E2E Kurta" }).click();
  await page.getByLabel("Quantity change").fill("-4");
  await page.getByLabel("Reason").selectOption("adjustment");
  await page.getByRole("button", { name: "Record stock change" }).click();
  await expect(page.getByLabel(/^In stock/)).toHaveValue("5");
  const history = page.getByRole("table", { name: /Stock history/ });
  await expect(history).toContainText("opening");
  await expect(history).toContainText("adjustment");

  // taking out more than is on the shelf is refused in words
  await page.getByLabel("Quantity change").fill("-50");
  await page.getByRole("button", { name: "Record stock change" }).click();
  await expect(page.getByText(/Not enough stock for E2E Kurta/)).toBeVisible();
});

test("staff can see products and stock but not add or change them", async ({ page }) => {
  await signIn(page, STAFF);
  await expect(page.getByRole("table", { name: "Products" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Add product" })).toHaveCount(0);
  await expect(page.getByRole("columnheader", { name: "Cost" })).toHaveCount(0);
  await visit(page, "/inventory/new");
  await expect(page.getByText(/access is restricted/i)).toBeVisible();
});
