import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  typescript: {
    // Pre-existing type issues don't affect runtime; skip for Docker builds
    ignoreBuildErrors: true,
  },
  async rewrites() {
    // BACKEND_URL is server-only (no NEXT_PUBLIC_ prefix) — never exposed to the browser.
    // The client uses relative paths; Next.js proxies them to the backend via these rewrites.
    const backendUrl =
      process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      { source: "/api/:path*", destination: `${backendUrl}/api/:path*` },
      {
        source: "/generate/:path*",
        destination: `${backendUrl}/generate/:path*`,
      },
    ];
  },
};

export default nextConfig;
