import { expect, test, type Page } from "@playwright/test";

/**
 * Task 20 acceptance, against the REAL backend: login, logout, session expiry and 403 for a role without access.
 * Needs the stack from `uv run python scripts/e2e_auth_stack.py` (it sets E2E_AUTH=1 and starts everything).
 */
test.skip(!process.env.E2E_AUTH, "run through scripts/e2e_auth_stack.py");

const PASSWORD = "e2e-password-1";

/** Navigate and wait until the page has settled. A reload that aborts an in-flight refresh loses the rotated cookie
 * (the server has already rotated it), which reuse detection then treats as theft: tests must not do that. */
async function open(page: Page, path: string) {
  await page.goto(path);
  await page.waitForLoadState("networkidle");
}

async function signIn(page: Page, email: string, password = PASSWORD) {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

test("a visitor who is not signed in is sent to sign-in and comes back afterwards", async ({ page }) => {
  await open(page, "/dashboard/orders");
  await expect(page).toHaveURL(/\/sign-in\?next=%2Fdashboard%2Forders/);
  await page.getByLabel("Email").fill("owner@example.com");
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard\/orders$/);
  await expect(page.getByText(/access is restricted/i)).toHaveCount(0);
});

test("the sign-in redirect keeps the query string of the page that was asked for", async ({ page }) => {
  await open(page, "/dashboard/orders?status=pending");
  await expect(page).toHaveURL(/next=%2Fdashboard%2Forders%3Fstatus%3Dpending/);
});

test("a wrong password shows an error and does not sign in", async ({ page }) => {
  await signIn(page, "owner@example.com", "not-the-password");
  await expect(page.locator("form[aria-label='Sign in'] [role=alert]")).toContainText("Invalid email or password");
  await expect(page).toHaveURL(/\/sign-in/);
});

test("the refresh token is an httpOnly cookie, never visible to page JavaScript", async ({ page, context }) => {
  await signIn(page, "owner@example.com");
  await expect(page).toHaveURL(/\/dashboard$/);
  const cookie = (await context.cookies()).find((c) => c.name === "bf_refresh");
  expect(cookie, "refresh cookie is set").toBeDefined();
  expect(cookie?.httpOnly).toBe(true);
  expect(cookie?.sameSite).toBe("Lax");
  const visible = await page.evaluate(() => ({
    cookie: document.cookie,
    stored: [...Object.entries(localStorage), ...Object.entries(sessionStorage)]
      .map(([k, v]) => `${k}=${v}`)
      .join(" | "),
  }));
  expect(visible.cookie).not.toContain("bf_refresh");
  expect(visible.stored).not.toMatch(/token|refresh|auth|eyJ/i); // the theme preference is fine; no credentials
});

test("a reload keeps the session (restored from the cookie) and API calls carry the token", async ({ page }) => {
  const unauthorized: string[] = [];
  page.on("response", (r) => {
    if (r.url().startsWith("http://localhost:8000/api/") && r.status() === 401) unauthorized.push(r.url());
  });
  await signIn(page, "owner@example.com");
  await expect(page).toHaveURL(/\/dashboard$/);
  await open(page, "/dashboard/inventory");
  await expect(page.getByText(/access is restricted/i)).toHaveCount(0);
  await page.waitForLoadState("networkidle");
  expect(unauthorized, "no API call may be rejected as unauthenticated").toEqual([]);
});

test("a staff member is shown the restricted view on owner and manager pages, and the work pages still open", async ({
  page,
}) => {
  await signIn(page, "staff@example.com");
  await expect(page).toHaveURL(/\/dashboard$/);
  await open(page, "/dashboard/settings");
  await expect(page.getByText(/access is restricted/i)).toBeVisible();
  await open(page, "/dashboard/marketing/overview");
  await expect(page.getByText(/access is restricted/i)).toBeVisible();
  await open(page, "/dashboard/orders");
  await expect(page.getByText(/access is restricted/i)).toHaveCount(0);
});

test("a manager can use marketing but not shop settings", async ({ page }) => {
  await signIn(page, "manager@example.com");
  await expect(page).toHaveURL(/\/dashboard$/);
  await open(page, "/dashboard/settings");
  await expect(page.getByText(/access is restricted/i)).toBeVisible();
  await open(page, "/dashboard/marketing/overview");
  await expect(page.getByText(/access is restricted/i)).toHaveCount(0);
  await open(page, "/dashboard/marketing/credentials"); // integrations are owner-only
  await expect(page.getByText(/access is restricted/i)).toBeVisible();
});

test("a staff member's visit to a restricted area makes no marketing API calls (guard sits above the provider)", async ({
  page,
}) => {
  const marketingCalls: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/marketing")) marketingCalls.push(r.url());
  });
  await signIn(page, "staff@example.com");
  await expect(page).toHaveURL(/\/dashboard$/);
  await open(page, "/dashboard/marketing/overview");
  await expect(page.getByText(/access is restricted/i)).toBeVisible();
  expect(marketingCalls).toEqual([]);
});

test("signing out ends the session: the cookie is gone and protected pages ask for sign-in again", async ({
  page,
  context,
}) => {
  await signIn(page, "owner@example.com");
  await expect(page).toHaveURL(/\/dashboard$/);
  await open(page, "/ui-preview"); // the app shell carries the Sign out control
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect.poll(async () => (await context.cookies()).some((c) => c.name === "bf_refresh")).toBe(false);
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/sign-in/);
});

test("the session survives access-token expiry: it is refreshed in the background (tokens last 1 minute here)", async ({
  page,
}) => {
  let refreshes = 0;
  page.on("response", (r) => {
    if (r.url().endsWith("/api/auth/refresh") && r.status() === 200) refreshes += 1;
  });
  await signIn(page, "owner@example.com");
  await expect(page).toHaveURL(/\/dashboard$/);
  const before = refreshes;
  await page.waitForTimeout(14_000); // a 60 s token is refreshed every 5 s (never in a tight loop)
  expect(refreshes - before).toBeGreaterThanOrEqual(2);
  expect(refreshes - before).toBeLessThan(6);
  await page.reload();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText(/access is restricted/i)).toHaveCount(0);
});
