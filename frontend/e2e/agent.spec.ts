import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { visit } from "./support";

/**
 * Tasks 37, 44, 45, 63, 64 acceptance, against the REAL backend with the scripted model (no API key needed): staff chat a
 * sale, it waits for a manager, the manager edits and approves it in the Approvals page, the stock and the order change,
 * the activity log shows it, and the owner's switch stops the assistant.
 * Needs the stack from `uv run python scripts/e2e_auth_stack.py` (it starts the API with LLM_PROVIDER=scripted).
 */
test.skip(!process.env.E2E_AUTH, "run through scripts/e2e_auth_stack.py");

const API = "http://localhost:8000/api/v1";
const PASSWORD = process.env.E2E_PASSWORD ?? "e2e-password-1";
const OWNER = process.env.E2E_OWNER_EMAIL ?? "owner@example.com";
const MANAGER = process.env.E2E_MANAGER_EMAIL ?? "manager@example.com";
const STAFF = process.env.E2E_STAFF_EMAIL ?? "staff@example.com";

async function signIn(page: Page, email: string, next: string) {
  await page.goto(`/sign-in?next=${encodeURIComponent(next)}`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(new RegExp(`${next}$`));
}

async function post(request: APIRequestContext, url: string, options: Parameters<APIRequestContext["post"]>[1]) {
  for (let attempt = 1; ; attempt++) {
    try {
      return await request.post(url, options);
    } catch (error) {
      if (attempt >= 3) throw error;
    }
  }
}
async function ownerToken(request: APIRequestContext): Promise<string> {
  const res = await post(request, `${API}/auth/login`, { data: { email: OWNER, password: PASSWORD } });
  return (await res.json()).access_token as string;
}
/** A product and a customer with names the scripted model can find by one word each. */
async function seed(request: APIRequestContext): Promise<{ product: string; customer: string; productId: string }> {
  const token = await ownerToken(request);
  const stamp = String(Date.now()).slice(-7);
  const product = `zorbak${stamp}`;
  const customer = `qadir${stamp}`;
  const made = await post(request, `${API}/inventory/`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { sku: `AGENT-${stamp}`, name: `Zorbak${stamp}`, price: "800.00", qty_on_hand: 10 },
  });
  expect(made.status()).toBe(201);
  const person = await post(request, `${API}/customers/`, { headers: { Authorization: `Bearer ${token}` }, data: { phone: `+92303${stamp}`, name: `Qadir${stamp}` } });
  expect(person.status()).toBe(201);
  return { product, customer, productId: (await made.json()).id as string };
}

async function chat(page: Page, text: string) {
  await page.getByLabel("Your message").fill(text);
  await page.getByRole("button", { name: "Send" }).click();
}

test("staff chat a sale; a manager edits and approves it; stock, order and activity follow", async ({ page, browser, request }) => {
  const { product, customer, productId } = await seed(request);

  // staff: draft first, then "yes" files a request instead of changing anything
  await signIn(page, STAFF, "/sales/chat");
  await expect(page.getByText("Tell me what you sold")).toBeVisible();
  await chat(page, `sell 2 ${product} to ${customer}`);
  await expect(page.getByText(/Draft sale for Qadir/)).toBeVisible();
  await expect(page.getByText(/total Rs 1,600\.00/)).toBeVisible();
  await chat(page, "yes");
  await expect(page.getByText(/Sent for approval/).first()).toBeVisible();
  await expect(page.getByText(/Waiting for a manager or the owner to approve it/).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Approve" })).toHaveCount(0);

  // nothing changed yet
  const token = await ownerToken(request);
  const before = await (await request.get(`${API}/inventory/${productId}`, { headers: { Authorization: `Bearer ${token}` } })).json();
  expect(before.qty_on_hand).toBe(10);

  // a manager sees it in Approvals with plain-words details, edits the quantity, and approves it
  const manager = await (await browser.newContext()).newPage();
  await signIn(manager, MANAGER, "/approvals");
  const card = manager.getByRole("article", { name: /Sale: Post a sale of Rs 1,600\.00/ }).first();
  await expect(card).toContainText("2 x Zorbak");
  await expect(card).toContainText("Customer: Qadir");
  await card.getByRole("button", { name: "Edit" }).click();
  await manager.getByLabel(/^Quantity: 2 x Zorbak/).fill("1");
  await manager.getByRole("button", { name: "Save changes" }).click();
  await expect(card).toContainText("Total Rs 800.00");
  await card.getByRole("button", { name: "Approve" }).click();
  await expect(card).toContainText("executed");

  // the stock came off by the EDITED quantity, and an order exists on the chat channel
  await expect.poll(async () => (await (await request.get(`${API}/inventory/${productId}`, { headers: { Authorization: `Bearer ${token}` } })).json()).qty_on_hand).toBe(9);
  await visit(manager, "/orders");
  await manager.getByRole("searchbox", { name: "Search" }).fill(customer);
  await expect(manager.getByRole("row", { name: /Qadir/ })).toContainText("Rs 800");

  // the activity log shows both turns and what the agent did, with no personal data
  await visit(manager, "/agent-activity");
  await expect(manager.getByRole("table", { name: "Agent runs" })).toBeVisible();
  await manager.getByRole("link").filter({ hasText: /\d{4}/ }).first().click();
  await expect(manager.getByText("What the agent did")).toBeVisible();
  await expect(manager.getByText("post_order").or(manager.getByText("find_product")).first()).toBeVisible();
  await expect(manager.locator("body")).not.toContainText(customer);
});

test("a manager can reject, and the owner's switch stops the assistant", async ({ page, browser, request }) => {
  const { product, customer } = await seed(request);
  await signIn(page, STAFF, "/sales/chat");
  await chat(page, `sell 1 ${product} to ${customer}`);
  await expect(page.getByText(/Draft sale for Qadir/)).toBeVisible();
  await chat(page, "yes");
  await expect(page.getByText(/Sent for approval/).first()).toBeVisible();

  const owner = await (await browser.newContext()).newPage();
  await signIn(owner, OWNER, "/approvals");
  const card = owner.getByRole("article", { name: /Sale: Post a sale of Rs 800\.00/ }).first();
  await card.getByRole("button", { name: "Reject" }).click();
  await owner.getByRole("button", { name: "Reject" }).last().click();
  await expect(owner.getByText("Give a reason of at least 3 characters")).toBeVisible();
  await owner.getByLabel(/^Why are you rejecting it/).fill("Customer cancelled");
  await owner.getByRole("button", { name: "Reject" }).last().click();
  await expect(card).toContainText("rejected");
  await expect(card).toContainText("Customer cancelled");

  // pause: the very next message is refused in words, with no tool run
  await visit(owner, "/agent-activity");
  await expect(owner.getByText("AI assistant", { exact: true })).toBeVisible();
  await owner.getByRole("button", { name: "Pause the assistant" }).click();
  await expect(owner.getByRole("button", { name: "Switch it on" })).toBeVisible();
  await chat(page, `sell 1 ${product}`);
  await expect(page.getByText(/The AI assistant is paused for this shop/)).toBeVisible();
  await owner.getByRole("button", { name: "Switch it on" }).click();
  await expect(owner.getByRole("button", { name: "Pause the assistant" })).toBeVisible();
  await chat(page, `sell 1 ${product}`);
  await expect(page.getByText(/Draft sale/).last()).toBeVisible();
});

test("staff cannot open approvals or the activity log", async ({ page }) => {
  await signIn(page, STAFF, "/dashboard");
  await visit(page, "/approvals");
  await expect(page.getByText(/access is restricted/i)).toBeVisible();
  await visit(page, "/agent-activity");
  await expect(page.getByText(/access is restricted/i)).toBeVisible();
});
