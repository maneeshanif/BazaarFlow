import { expect, test } from "@playwright/test";

/**
 * Task 35 acceptance, against the REAL backend: a visitor creates an account and a shop through the form, is signed in
 * and lands in an empty shop; refusals (weak password, taken email) are explained under the right field.
 * Needs the stack from `uv run python scripts/e2e_auth_stack.py`.
 */
test.skip(!process.env.E2E_AUTH, "run through scripts/e2e_auth_stack.py");

test("a visitor creates a shop, is signed in, and lands in an empty shop with the next step offered", async ({ page }) => {
  const email = `new-${Date.now()}@example.com`;
  await page.goto("/register");

  await page.getByRole("button", { name: "Create shop" }).click();
  await expect(page.getByText("Your name needs at least 2 characters")).toBeVisible();
  await expect(page.getByText("You need to accept the terms to create an account")).toBeVisible();

  await page.getByLabel(/^Your name/).fill("Sana Malik");
  await page.getByLabel(/^Shop name/).fill("Sana Boutique");
  await page.getByLabel(/^Email/).fill(email);
  await page.getByLabel(/^Password/).fill("password123");
  await page.getByLabel(/^Phone/).fill("0300 1234567");
  await page.getByLabel(/^City/).fill("Lahore");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Create shop" }).click();

  // a common password is refused by the API and explained under the field; nothing was created
  await expect(page.getByText(/too common/)).toBeVisible();
  await expect(page).toHaveURL(/\/register$/);

  await page.getByLabel(/^Password/).fill("unusual-passphrase-42");
  await page.getByRole("button", { name: "Create shop" }).click();

  // signed in, inside the new shop, with the first step in front of them
  await expect(page).toHaveURL(/\/inventory$/);
  await expect(page.getByText("Sana Boutique")).toBeVisible();
  await expect(page.getByText("You have not added any products yet.")).toBeVisible();
  const cookie = (await page.context().cookies()).find((c) => c.name === "bf_refresh");
  expect(cookie?.httpOnly, "the session was stored in an httpOnly cookie").toBe(true);
  await page.getByRole("link", { name: "Add your first product" }).click();
  await expect(page).toHaveURL(/\/inventory\/new$/);
});

test("registering with an email that already has an account points to sign in", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel(/^Your name/).fill("Owner Again");
  await page.getByLabel(/^Shop name/).fill("Second Shop");
  await page.getByLabel(/^Email/).fill(process.env.E2E_OWNER_EMAIL ?? "owner@example.com");
  await page.getByLabel(/^Password/).fill("unusual-passphrase-42");
  await page.getByLabel(/^Phone/).fill("+923001234567");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Create shop" }).click();
  await expect(page.getByText("That email already has an account. Sign in instead.")).toBeVisible();
  await expect(page).toHaveURL(/\/register$/);
});
