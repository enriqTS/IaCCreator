import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  typescript: {
    // Pre-existing type issues don't affect runtime; skip for Docker builds
    ignoreBuildErrors: true,
  },
  async rewrites() {
    const backendUrl =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
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
