import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import { visit } from "./support";

/**
 * Tasks 38 and 39 acceptance, against the REAL backend and database: record a sale on credit, see the stock and the
 * customer's udhaar change, take a payment, reverse the sale, and check a staff member can sell but not reverse.
 * Needs the stack from `uv run python scripts/e2e_auth_stack.py`.
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

/** Test data through the API as the owner (the UI paths for these are covered by their own specs). */
async function post(request: APIRequestContext, url: string, options: Parameters<APIRequestContext["post"]>[1]) {
  for (let attempt = 1; ; attempt++) {
    try {
      return await request.post(url, options); // a kept-alive socket the server closed while idle fails once: try again
    } catch (error) {
      if (attempt >= 3) throw error;
    }
  }
}
async function ownerToken(request: APIRequestContext): Promise<string> {
  const res = await post(request, `${API}/auth/login`, { data: { email: OWNER, password: PASSWORD } });
  return (await res.json()).access_token as string;
}
async function makeProduct(request: APIRequestContext, name: string, price: string, qty: number): Promise<{ id: string; sku: string }> {
  const token = await ownerToken(request);
  const sku = `E2E-${name.replace(/\W/g, "")}-${Date.now()}`;
  const res = await post(request, `${API}/inventory/`, { headers: { Authorization: `Bearer ${token}` }, data: { sku, name, price, qty_on_hand: qty } });
  expect(res.status()).toBe(201);
  return { id: (await res.json()).id as string, sku };
}
async function makeCustomer(request: APIRequestContext, name: string): Promise<void> {
  const token = await ownerToken(request);
  const phone = `+92302${String(Date.now()).slice(-7)}`;
  const res = await post(request, `${API}/customers/`, { headers: { Authorization: `Bearer ${token}` }, data: { phone, name } });
  expect(res.status()).toBe(201);
}

async function addProduct(page: Page, search: string, name: string) {
  await page.getByRole("button", { name: "Add product" }).click();
  await page.getByRole("searchbox", { name: /Add a product/ }).fill(search);
  await page.getByRole("button", { name: new RegExp(name) }).click();
}

test("an owner sells on credit, takes a payment, and reverses the sale", async ({ page, request }) => {
  const product = await makeProduct(request, "Credit Kurta", "1000.00", 10);
  await makeCustomer(request, "Credit Customer");
  await signIn(page, OWNER, "/sales/new");

  // nothing to post yet
  await page.getByRole("button", { name: "Post sale" }).click();
  await expect(page.getByText("Add at least one item to the sale")).toBeVisible();

  await addProduct(page, product.sku, "Credit Kurta");
  await page.getByLabel("Quantity of Credit Kurta").fill("3");
  await expect(page.getByLabel("Sale totals").getByText("Rs 3,000").first()).toBeVisible(); // added up by the server

  // a sale on credit needs a customer
  await page.getByLabel(/^Paid by/).selectOption("udhaar");
  await expect(page.getByRole("button", { name: "Post sale" })).toBeEnabled();
  await page.getByRole("button", { name: "Post sale" }).click();
  await expect(page.getByText(/Choose the customer/)).toBeVisible();

  await page.getByRole("button", { name: /Customer: Walk-in customer/ }).click();
  await page.getByRole("searchbox", { name: /Find a customer/ }).fill("Credit Customer");
  await page.getByRole("button", { name: /^Credit Customer/ }).click();
  await expect(page.getByRole("button", { name: /Customer: Credit Customer/ })).toBeVisible();
  await expect(page.getByLabel("Sale totals")).toContainText("On credit (udhaar)");
  await page.getByRole("button", { name: "Post sale" }).click();

  // the order opens: posted, all of it still owed
  await expect(page).toHaveURL(/\/orders\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { name: /^Order / })).toBeVisible();
  await expect(page.getByText("posted", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Order totals")).toContainText("Rs 3,000");
  const orderUrl = page.url();

  // the stock came off the shelf
  await visit(page, "/inventory");
  await page.getByRole("searchbox", { name: "Search" }).fill(product.sku);
  await expect(page.getByRole("row", { name: new RegExp(product.sku) })).toContainText("7");

  // the customer owes it, and a payment brings it down
  await visit(page, "/customers");
  await page.getByRole("searchbox", { name: "Search" }).fill("Credit Customer");
  const row = page.getByRole("row", { name: /Credit Customer/ });
  await expect(row).toContainText("Rs 3,000");
  await expect(row).toContainText("owes");
  await row.getByRole("link", { name: "Credit Customer" }).click();
  await expect(page.getByLabel("Balance")).toHaveText("Rs 3,000");
  await page.getByLabel(/^Amount received/).fill("5000");
  await page.getByRole("button", { name: "Record payment" }).click();
  await expect(page.getByText("They only owe Rs 3,000")).toBeVisible();
  await page.getByLabel(/^Amount received/).fill("1000");
  await page.getByRole("button", { name: "Record payment" }).click();
  await expect(page.getByLabel("Balance")).toHaveText("Rs 2,000");
  await expect(page.getByText("Payment received")).toBeVisible();
  await expect(page.getByText("Sale on credit")).toBeVisible();

  // reverse the sale: the stock returns and the sale stays on record as reversed
  await visit(page, orderUrl);
  await page.getByRole("button", { name: "Reverse sale" }).click();
  await page.getByRole("button", { name: "Reverse sale" }).last().click();
  await expect(page.getByText("Give a reason of at least 3 characters")).toBeVisible();
  await page.getByLabel(/^Why is it being reversed/).fill("Wrong colour");
  await page.getByRole("button", { name: "Reverse sale" }).last().click();
  await expect(page.getByText("reversed", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Reverse sale" })).toHaveCount(0);
  await visit(page, "/inventory");
  await page.getByRole("searchbox", { name: "Search" }).fill(product.sku);
  await expect(page.getByRole("row", { name: new RegExp(product.sku) })).toContainText("10");
});

test("a staff member sells for cash, sees no cost, and cannot reverse", async ({ page, request }) => {
  const product = await makeProduct(request, "Cash Scarf", "250.00", 5);
  await signIn(page, STAFF, "/sales/new");
  await addProduct(page, product.sku, "Cash Scarf");
  await page.getByLabel("Quantity of Cash Scarf").fill("2");
  await expect(page.getByLabel("Sale totals").getByText("Rs 500").first()).toBeVisible();

  // asking for more than the shelf has is explained, and staff are not offered an override
  await page.getByLabel("Quantity of Cash Scarf").fill("9");
  await expect(page.getByText(/Not enough stock for Cash Scarf/)).toBeVisible();
  await expect(page.getByRole("checkbox", { name: /Sell more than the shelf count/ })).toHaveCount(0);
  await page.getByLabel("Quantity of Cash Scarf").fill("2");

  await page.getByRole("button", { name: "Post sale" }).click();
  await expect(page).toHaveURL(/\/orders\/[0-9a-f-]{36}$/);
  await expect(page.getByLabel("Order totals")).toContainText("Rs 500");
  await expect(page.getByRole("columnheader", { name: "Cost" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Reverse sale" })).toHaveCount(0);
});
