import { expect, test } from "@playwright/test";

const widths = [
  { name: "phone", width: 360, height: 800 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "laptop", width: 1280, height: 800 },
  { name: "desktop", width: 1440, height: 900 },
];

for (const vp of widths) {
  test(`the app shell does not scroll horizontally at ${vp.name} (${vp.width}px)`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.goto("/ui-preview");
    await expect(page.getByRole("main")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, "page body must not scroll horizontally").toBeLessThanOrEqual(0);
  });
}

test("a wide data grid scrolls inside its own container on a phone", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto("/ui-preview");
  const scroller = page.getByTestId("table-scroll").first();
  const { scrollWidth, clientWidth } = await scroller.evaluate((el) => ({
    scrollWidth: el.scrollWidth,
    clientWidth: el.clientWidth,
  }));
  expect(scrollWidth).toBeGreaterThan(clientWidth);
  const bodyOverflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(bodyOverflow).toBeLessThanOrEqual(0);
});

test("the sidebar is a drawer on phones and persistent on desktop", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto("/ui-preview");
  await expect(page.getByRole("navigation", { name: /primary tabs/i })).toBeVisible();
  await expect(page.locator("aside[data-testid='sidebar']")).toBeHidden();
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(page.locator("aside[data-testid='sidebar']")).toBeVisible();
});
