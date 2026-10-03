import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { visit } from "./support";

/**
 * Tasks 36 and 48 acceptance, against the REAL backend: the home screen shows the figures the API computes, an owner
 * sees every card and the briefing, staff never see profit, udhaar, approvals or the briefing, and a new sale changes
 * the orders figure. Needs the stack from `uv run python scripts/e2e_auth_stack.py`.
 */
test.skip(!process.env.E2E_AUTH, "run through scripts/e2e_auth_stack.py");

const API = "http://localhost:8000/api/v1";
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

async function token(request: APIRequestContext): Promise<string> {
  for (let attempt = 1; ; attempt++) {
    try {
      const res = await request.post(`${API}/auth/login`, { data: { email: OWNER, password: PASSWORD } });
      return (await res.json()).access_token as string;
    } catch (error) {
      if (attempt >= 3) throw error;
    }
  }
}

test("an owner sees every card and the briefing; a new sale changes the orders figure", async ({ page, request }) => {
  const auth = { Authorization: `Bearer ${await token(request)}` };
  const before = await (await request.get(`${API}/dashboard/summary`, { headers: auth })).json();

  await signIn(page, OWNER, "/dashboard");
  const figures = page.getByRole("region", { name: "Key figures" });
  await expect(figures.getByRole("link", { name: /Today sales/ })).toBeVisible();
  await expect(figures.getByRole("link", { name: /Today profit/ })).toBeVisible();
  await expect(figures.getByRole("link", { name: /Low-stock items/ })).toBeVisible();
  await expect(figures.getByRole("link", { name: /Unpaid udhaar/ })).toBeVisible();
  await expect(figures.getByRole("link", { name: /Approvals waiting/ })).toBeVisible();
  await expect(page.getByRole("region", { name: "Briefing" })).toBeVisible();
  await expect(figures.getByRole("link", { name: /Today orders/ })).toContainText(String(before.orders.value));

  // post a sale through the API, then the figure follows after a reload
  const stamp = String(Date.now()).slice(-7);
  const made = await request.post(`${API}/inventory/`, { headers: auth, data: { sku: `DASH-${stamp}`, name: `Dash${stamp}`, price: "100.00", cost: "60.00", qty_on_hand: 5 } });
  expect(made.status()).toBe(201);
  const sold = await request.post(`${API}/sales/`, {
    headers: { ...auth, "Idempotency-Key": `dash-${stamp}` },
    data: { items: [{ product_id: (await made.json()).id, qty: 1 }], payment_method: "cash" },
  });
  expect(sold.status()).toBe(201);
  await visit(page, "/dashboard");
  await expect(figures.getByRole("link", { name: /Today orders/ })).toContainText(String(before.orders.value + 1));

  // the period filter asks the server again
  await page.getByLabel("Period", { exact: true }).selectOption("7d");
  await expect(figures.getByRole("link", { name: /Last 7 days sales/ })).toBeVisible();
  await expect(page.getByRole("table", { name: "Sales per day, last 7 days" })).toBeAttached();

  // a card drills down to the records behind it
  await figures.getByRole("link", { name: /Approvals waiting/ }).click();
  await expect(page).toHaveURL(/\/approvals$/);
});

test("staff see sales, orders and low stock only", async ({ page }) => {
  await signIn(page, STAFF, "/dashboard");
  const figures = page.getByRole("region", { name: "Key figures" });
  await expect(figures.getByRole("link", { name: /Today sales/ })).toBeVisible();
  await expect(figures.getByRole("link")).toHaveCount(3);
  await expect(page.getByRole("region", { name: "Briefing" })).toHaveCount(0);
  await expect(page.getByText(/profit/i)).toHaveCount(0);
});
