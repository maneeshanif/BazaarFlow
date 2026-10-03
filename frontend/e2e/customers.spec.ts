import { expect, test, type Page } from "@playwright/test";

/**
 * Task 40 acceptance, against the REAL backend: an owner adds a customer through the form, finds them in the list,
 * edits them, and a staff member is kept out of the customers area. (Credit sales and payments are exercised in the
 * sales spec, because udhaar is created by selling on credit.)
 * Needs the stack from `uv run python scripts/e2e_auth_stack.py`.
 */
test.skip(!process.env.E2E_AUTH, "run through scripts/e2e_auth_stack.py");

const PASSWORD = process.env.E2E_PASSWORD ?? "e2e-password-1";
const OWNER = process.env.E2E_OWNER_EMAIL ?? "owner@example.com";
const STAFF = process.env.E2E_STAFF_EMAIL ?? "staff@example.com";

async function signIn(page: Page, email: string, next: string) {
  await page.goto(`/sign-in?next=${encodeURIComponent(next)}`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(new RegExp(`${next}$`));
}

test("an owner adds, finds and edits a customer", async ({ page }) => {
  const suffix = String(Date.now()).slice(-7);
  await signIn(page, OWNER, "/customers");
  await page.getByRole("link", { name: "Add customer" }).first().click();

  await page.getByRole("button", { name: "Add customer" }).click();
  await expect(page.getByText("Enter a phone number like 0300 1234567")).toBeVisible();

  await page.getByLabel(/^Phone/).fill(`0301${suffix}`);
  await page.getByLabel(/^Name/).fill("E2E Customer");
  await page.getByLabel(/^Address/).fill("Model Town, Lahore");
  await page.getByRole("button", { name: "Add customer" }).click();

  // lands on the customer, with an empty udhaar ledger
  await expect(page).toHaveURL(/\/customers\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { name: "E2E Customer" })).toBeVisible();
  await expect(page.getByText("No credit sales or payments yet.")).toBeVisible();
  await expect(page.getByLabel("Balance")).toHaveText("Rs 0");

  // the same phone twice is refused under the phone field
  await page.goto("/customers/new");
  await page.getByLabel(/^Phone/).fill(`0301${suffix}`);
  await page.getByRole("button", { name: "Add customer" }).click();
  await expect(page.getByText("A customer with this phone number already exists")).toBeVisible();

  // found by search, stored in international form
  await page.goto("/customers");
  await page.getByRole("searchbox", { name: "Search" }).fill("E2E Customer");
  const row = page.getByRole("row", { name: /E2E Customer/ });
  await expect(row).toContainText(`+92301${suffix}`);
  await expect(row).toContainText("settled");

  // edit
  await row.getByRole("link", { name: "E2E Customer" }).click();
  await page.getByLabel(/^Name/).fill("E2E Customer Renamed");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("heading", { name: "E2E Customer Renamed" })).toBeVisible();
});

test("staff are kept out of the customers area", async ({ page }) => {
  await signIn(page, STAFF, "/dashboard");
  await page.goto("/customers");
  await expect(page.getByText(/access is restricted/i)).toBeVisible();
  await expect(page.getByRole("link", { name: "Customers" })).toHaveCount(0);
});
