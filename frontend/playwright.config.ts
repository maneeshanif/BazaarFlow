import { defineConfig } from "@playwright/test";

// The shell test runs against a production build: `npm run build` first (verify.sh --slow does).
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  // the real-stack specs share one owner account, and ending one session on token reuse (by design) ends them all:
  // run them one at a time so a session event in one test cannot sign out another
  workers: process.env.E2E_AUTH ? 1 : undefined,
  reporter: [["list"]],
  use: { baseURL: "http://localhost:3100", trace: "retain-on-failure" },
  webServer: {
    command: "npx next start -p 3100",
    url: "http://localhost:3100/ui-preview",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: { UI_PREVIEW: "1" },
  },
});
