import { expect, test, type Page } from "@playwright/test";

import { visit } from "./support";

/**
 * Task 43 acceptance, against the REAL backend: an owner adds a manager, the manager signs in and sees manager
 * pages, the owner turns them into staff and the pages follow, and removing them locks them out.
 * Needs the stack from `uv run python scripts/e2e_auth_stack.py`.
 */
test.skip(!process.env.E2E_AUTH, "run through scripts/e2e_auth_stack.py");

const PASSWORD = process.env.E2E_PASSWORD ?? "e2e-password-1";
const OWNER = process.env.E2E_OWNER_EMAIL ?? "owner@example.com";
const MANAGER = process.env.E2E_MANAGER_EMAIL ?? "manager@example.com";

async function signIn(page: Page, email: string, password: string, next: string) {
  await page.goto(`/sign-in?next=${encodeURIComponent(next)}`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

test("an owner adds a team member, changes their role, and removes them", async ({ page, browser }) => {
  const email = `team-${Date.now()}@example.com`;
  const password = "first-pass-2026";

  await signIn(page, OWNER, PASSWORD, "/team");
  await expect(page).toHaveURL(/\/team$/);
  await expect(page.getByText("(you)")).toBeVisible();

  // adding: checked first, then created
  await page.getByRole("link", { name: "Add team member" }).first().click();
  await page.getByRole("button", { name: "Add to team" }).click();
  await expect(page.getByText("Name needs at least 2 characters")).toBeVisible();
  await page.getByLabel(/^Name/).fill("Nadia Manager");
  await page.getByLabel(/^Email/).fill(email);
  await page.getByLabel(/^Role/).selectOption("manager");
  await page.getByLabel(/^First password/).fill("12345678");
  await page.getByRole("button", { name: "Add to team" }).click();
  await expect(page.getByText(/too common/)).toBeVisible();
  await page.getByLabel(/^First password/).fill(password);
  await page.getByRole("button", { name: "Add to team" }).click();
  await expect(page).toHaveURL(/\/team$/);
  const row = page.getByRole("row", { name: /Nadia Manager/ });
  await expect(row).toContainText(email);
  await expect(row.getByLabel("Role of Nadia Manager")).toHaveValue("manager");

  // the new manager signs in (a separate browser) and can use manager pages but not the team page
  const theirs = await (await browser.newContext()).newPage();
  await signIn(theirs, email, password, "/customers");
  await expect(theirs).toHaveURL(/\/customers$/);
  await expect(theirs.getByRole("heading", { name: "Customers" })).toBeVisible();
  await visit(theirs, "/team");
  await expect(theirs.getByText(/access is restricted/i)).toBeVisible();

  // the owner makes them staff: the customers area closes to them on their next page
  await row.getByLabel("Role of Nadia Manager").selectOption("staff");
  await expect(row.getByLabel("Role of Nadia Manager")).toHaveValue("staff");
  await visit(theirs, "/customers");
  await expect(theirs.getByText(/access is restricted/i)).toBeVisible();

  // the owner removes them: they are asked to sign in and cannot get back in
  await row.getByRole("button", { name: "Remove Nadia Manager" }).click();
  await page.getByRole("button", { name: "Remove from team" }).click();
  await expect(page.getByRole("row", { name: /Nadia Manager/ })).toHaveCount(0);
  const again = await (await browser.newContext()).newPage();
  await signIn(again, email, password, "/dashboard");
  await expect(again.getByText(/not part of any shop/i)).toBeVisible();
});

test("a manager cannot open the team page", async ({ page }) => {
  await signIn(page, MANAGER, PASSWORD, "/dashboard");
  await expect(page).toHaveURL(/\/dashboard$/);
  await visit(page, "/team");
  await expect(page.getByText(/access is restricted/i)).toBeVisible();
  await expect(page.getByRole("link", { name: "Team" })).toHaveCount(0);
});
