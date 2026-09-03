import type { NextConfig } from "next";
import { loadEnvConfig } from "@next/env";
import path from "node:path";

const webDir = __dirname;
const repoRoot = path.resolve(webDir, "../..");
loadEnvConfig(repoRoot);
for (const key of [
  "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
  "CLERK_SECRET_KEY",
  "NEXT_PUBLIC_CLERK_SIGN_IN_URL",
  "NEXT_PUBLIC_CLERK_SIGN_UP_URL",
]) {
  if (!process.env[key]) {
    delete process.env[key];
  }
}
loadEnvConfig(webDir);

const nextConfig: NextConfig = {
  output: "standalone",
};

export default nextConfig;
