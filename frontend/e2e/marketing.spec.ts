import { expect, test, type Page } from "@playwright/test";
import { visit } from "./support";

/**
 * Task 42 acceptance, against the REAL backend with the scripted writer (no API key needed): a manager drafts a post,
 * edits it, sends it for approval; the owner approves it; staff cannot open the studio.
 * Needs the stack from `uv run python scripts/e2e_auth_stack.py` (it starts the API with LLM_PROVIDER=scripted).
 */
test.skip(!process.env.E2E_AUTH, "run through scripts/e2e_auth_stack.py");

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

test("a manager drafts, edits and sends a post; the owner approves it", async ({ page, browser }) => {
  await signIn(page, MANAGER, "/marketing");
  await expect(page.getByRole("heading", { name: "Marketing studio" })).toBeVisible();

  // promoting a product needs a product
  await page.getByLabel(/What is the post for/).selectOption("promote_product");
  await page.getByRole("button", { name: "Write the draft" }).click();
  await expect(page.getByText("Choose the product to promote")).toBeVisible();

  // a general draft instead: the assistant writes it and the editor opens
  await page.getByLabel(/What is the post for/).selectOption("general");
  await page.getByRole("button", { name: "Write the draft" }).click();
  await expect(page).toHaveURL(/\/marketing\/[0-9a-f-]{36}$/);
  await expect(page.getByLabel(/^Message/)).not.toHaveValue("");

  // edit with a unique title and tidy hashtags
  const title = `Eid offer ${Date.now()}`;
  await page.getByLabel(/^Title/).fill(title);
  await page.getByLabel(/^Hashtags/).fill("eid  offer");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByLabel(/^Hashtags/)).toHaveValue("#eid #offer");
  await page.getByRole("button", { name: "Send for approval" }).click();
  await expect(page.getByText(/Waiting for a manager or the owner/)).toBeVisible();
  await expect(page.getByLabel(/^Title/)).toHaveAttribute("readonly", "");

  // the owner sees it with the text, and approves it
  const owner = await (await browser.newContext()).newPage();
  await signIn(owner, OWNER, "/approvals");
  const card = owner.getByRole("article", { name: new RegExp(`Marketing post: Approve the post: ${title}`) });
  await expect(card).toContainText("Nothing is posted to Facebook yet");
  await expect(card.getByRole("button", { name: "Edit" })).toHaveCount(0);
  await card.getByRole("button", { name: "Approve" }).click();
  await expect(card).toContainText("executed");

  // back in the studio the post is approved and read-only
  await visit(page, "/marketing");
  await page.getByLabel("Show").selectOption("approved");
  await page.getByRole("link", { name: title }).click();
  await expect(page.getByText(/Approved and ready/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Save changes" })).toHaveCount(0);
});

test("a draft can be removed after a confirmation", async ({ page }) => {
  await signIn(page, MANAGER, "/marketing");
  await page.getByRole("button", { name: "Write the draft" }).click();
  await expect(page).toHaveURL(/\/marketing\/[0-9a-f-]{36}$/);
  const url = page.url();
  await page.getByRole("button", { name: "Remove draft" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Remove draft" }).click();
  await expect(page).toHaveURL(/\/marketing$/);
  await page.goto(url);
  await expect(page.getByText("That post does not exist.")).toBeVisible();
});

test("staff cannot open the marketing studio", async ({ page }) => {
  await signIn(page, STAFF, "/dashboard");
  await visit(page, "/marketing");
  await expect(page.getByText(/access is restricted/i)).toBeVisible();
});
