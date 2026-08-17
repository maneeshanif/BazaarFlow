import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone", // enables the minimal Docker build
};

export default nextConfig;
