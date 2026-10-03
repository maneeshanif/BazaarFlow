import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const nextConfig: NextConfig = {
  output: "standalone", // enables the minimal Docker build
};

export default withSentryConfig(nextConfig, {
  org: "anees-3m",
  project: "bazarflow-frontend",
  // Auth token for source map uploads — set SENTRY_AUTH_TOKEN in your env
  authToken: process.env.SENTRY_AUTH_TOKEN,
  // Upload more client files for better stack traces
  widenClientFileUpload: true,
  // Route Sentry browser requests through Next.js to avoid ad blockers
  tunnelRoute: "/monitoring",
  // Suppress build output outside of CI
  silent: !process.env.CI,
});
