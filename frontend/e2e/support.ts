import type { Page } from "@playwright/test";

/**
 * Open a page of the signed-in app. A hard navigation that aborts a token refresh in flight loses the rotated cookie
 * (the server has already rotated it) and can sign the test out; the real stack here refreshes every 5 s because its
 * tokens last a minute. So wait for the current page to go quiet before leaving it, and for the next one to settle.
 */
export async function visit(page: Page, path: string): Promise<void> {
  await page.waitForLoadState("networkidle");
  await page.goto(path);
  await page.waitForLoadState("networkidle");
}
