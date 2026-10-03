import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { visit } from "./support";

/**
 * Task 53 acceptance: axe finds no serious or critical accessibility issue on the slice (WCAG 2.1 A and AA rules),
 * on the public pages and on every signed-in screen the owner uses. Needs the stack from
 * `uv run python scripts/e2e_auth_stack.py`.
 */
test.skip(!process.env.E2E_AUTH, "run through scripts/e2e_auth_stack.py");

const PASSWORD = process.env.E2E_PASSWORD ?? "e2e-password-1";
const OWNER = process.env.E2E_OWNER_EMAIL ?? "owner@example.com";

async function audit(page: Page, label: string) {
  const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  const blocking = result.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  const summary = blocking.map((v) => `${v.id} (${v.impact}): ${v.nodes.slice(0, 3).map((n) => `${n.target.join(" ")} :: ${n.html.slice(0, 110)} :: ${n.any[0]?.message ?? ""}`).join(" | ")}`);
  expect(summary, `${label}: serious or critical accessibility issues`).toEqual([]);
}

for (const path of ["/", "/demo", "/sign-in", "/register"]) {
  test(`public page ${path} has no serious accessibility issue`, async ({ page }) => {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    await audit(page, path);
  });
}

const SCREENS: [string, string][] = [
  ["/dashboard", "Home"],
  ["/inventory", "Products"],
  ["/inventory/new", "Add product"],
  ["/customers", "Customers"],
  ["/sales/new", "New sale"],
  ["/orders", "Orders"],
  ["/team", "Team"],
  ["/sales/chat", "Sales chat"],
  ["/approvals", "Approvals"],
  ["/agent-activity", "Agent activity"],
  ["/marketing", "Marketing studio"],
];

test("every signed-in screen has no serious accessibility issue", async ({ page }) => {
  test.setTimeout(240_000);
  await page.goto("/sign-in?next=/dashboard");
  await page.getByLabel("Email").fill(OWNER);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  for (const [path, heading] of SCREENS) {
    await visit(page, path);
    await expect(page.getByRole("heading", { name: heading, exact: false }).first()).toBeVisible();
    await page.waitForLoadState("networkidle");
    await audit(page, path);
  }
});
